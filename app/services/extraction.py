# Nghiệp vụ trích xuất: regex (cách 1), AI trả JSON (cách 2), AI + Function Calling (cách 3).
import json
import re
from datetime import date
from time import perf_counter

from fastapi import HTTPException

from app.config import PROMPT
from app.schemas import Booking
from app.services import ai_gateway
from app.services.inventory import TOOL, check_room_availability


def extract_regex(text):
    room = re.search(r'\b(STANDARD|DELUXE|SUITE)\b', text, re.I)
    dates = re.findall(r'\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b', text)
    parsed = []
    for value in dates[:2]:
        if '/' in value:
            day, month, year = map(int, value.split('/'))
            parsed.append(date(year, month, day))
        else:
            parsed.append(date.fromisoformat(value))
    return Booking(room_type=room.group().upper() if room else None,
                   check_in=parsed[0] if parsed else None,
                   check_out=parsed[1] if len(parsed) > 1 else None)


async def run_extraction(request, prompt=PROMPT, config=None, diagnostic=None, history=()):
    started = perf_counter()
    messages = [{'role': 'system', 'content': prompt}, *history, {'role': 'user', 'content': request.raw_text}]

    async def call(messages, **options):
        if diagnostic is not None:
            diagnostic['requests'].append({'messages': list(messages), **options})
        result = await ai_gateway.chat(messages, config_override=config, **options)
        if diagnostic is not None:
            diagnostic['raw_responses'].append(result.get('choices', []))
            diagnostic['total_tokens'] += result.get('usage', {}).get('total_tokens', 0)
        return result
    tokens = 0
    trace = []
    availability = None
    reply = None
    stage = None
    try:
        if request.mode == 'regex':
            booking = extract_regex(request.raw_text)
        else:
            # Lượt 1: AI trích xuất JSON, Pydantic kiểm tra
            result = await call(messages, response_format={'type': 'json_object'})
            tokens += result.get('usage', {}).get('total_tokens', 0)
            stage = 'output_validation'
            booking = Booking.model_validate_json(result['choices'][0]['message']['content'])
            stage = None
        complete = all(value is not None for value in booking.model_dump().values())
        if complete and request.mode == 'tools':
            # Lượt 2: AI đề xuất tool, backend so khớp rồi mới chạy
            messages += [{'role': 'assistant', 'content': booking.model_dump_json()},
                         {'role': 'user', 'content': 'Gọi tool kiểm tra booking đã trích xuất.'}]
            result = await call(messages, tools=[TOOL], parallel_tool_calls=False,
                tool_choice={'type': 'function', 'function': {'name': 'check_room_availability'}})
            tokens += result.get('usage', {}).get('total_tokens', 0)
            stage = 'tool_validation'
            message = result['choices'][0]['message']
            calls = message.get('tool_calls', [])
            if len(calls) != 1 or calls[0]['function']['name'] != 'check_room_availability':
                raise ValueError('Tool call không hợp lệ')
            tool_call = calls[0]
            arguments = Booking.model_validate_json(tool_call['function']['arguments'])
            if arguments != booking:
                raise ValueError('Tool arguments khác booking đã xác thực')
            availability = check_room_availability(**arguments.model_dump(mode='json'))
            stage = None
            trace = [{'tool': tool_call['function']['name'], 'arguments': arguments.model_dump(mode='json'), 'result': availability}]
            # Lượt 3: gửi kết quả tool, AI viết câu trả lời
            messages += [message, {'role': 'tool', 'tool_call_id': tool_call['id'], 'content': json.dumps(availability)},
                         {'role': 'user', 'content': 'Trả lời ngắn bằng tiếng Việt dựa trên kết quả tool. Không trả JSON.'}]
            final = await call(messages)
            tokens += final.get('usage', {}).get('total_tokens', 0)
            reply = final['choices'][0]['message']['content']
        return {'mode': request.mode, 'booking': booking.model_dump(mode='json'),
                'status': 'EXTRACTED' if complete else 'NEED_MORE_INFO',
                'availability': availability, 'tool_trace': trace, 'reply': reply,
                'total_tokens': tokens, 'elapsed_ms': round((perf_counter() - started) * 1000, 2)}
    except (ValueError, KeyError, IndexError, TypeError) as error:
        if diagnostic is not None and stage:
            diagnostic['failure_stage'] = stage
        raise HTTPException(422 if request.mode == 'regex' else 502,
                            'Dữ liệu ngày không hợp lệ' if request.mode == 'regex' else 'Phản hồi AI/tool không hợp lệ') from error
