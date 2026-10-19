# Trang giao diện, cấu hình gateway và lab thử prompt. Chỉ dùng trên máy local.
import json
from pathlib import Path
from time import perf_counter

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.dependencies import is_local, local_admin
from app.schemas import ExperimentInput, GatewayInput, ModelInput
from app.services import ai_gateway
from app.services.extraction import run_extraction

router = APIRouter(tags=['gateway (local)'])
UI_FILE = Path(__file__).resolve().parent.parent / 'static' / 'ui.html'


@router.get('/', response_class=HTMLResponse, include_in_schema=False)
def home(request: Request):
    local = is_local(request)
    page = UI_FILE.read_text(encoding='utf-8')
    # Chèn vào chuỗi JS nháy đơn hay kép đều an toàn, dù editor có format lại ui.html
    model = json.dumps(ai_gateway.gateway['model'] if local else '')[1:-1].replace("'", '\\u0027').replace('<', '\\u003c')
    page = (page.replace('__ADMIN_TOKEN__', ai_gateway.ADMIN_TOKEN if local else '')
                .replace('__ACTIVE_MODEL__', model)
                .replace('__GATEWAY_SOURCE__', ai_gateway.source if local else ''))
    return HTMLResponse(page, headers={'Cache-Control': 'no-store', 'X-Frame-Options': 'DENY'})


@router.post('/api/gateway/models')
async def gateway_models(body: GatewayInput, request: Request):
    local_admin(request)
    # Chỉ ghi nhận để "Sử dụng model" áp dụng; cấu hình đang chạy (vd từ .env) giữ nguyên dù kết nối lỗi
    ai_gateway.pending.clear()
    ai_gateway.pending.update(base_url=body.base_url, api_key=body.api_key)
    result = await ai_gateway.gateway_request({**ai_gateway.pending, 'model': ''}, '/models')
    try:
        models = sorted({row['id'] for row in result['data'] if isinstance(row.get('id'), str)})
    except (KeyError, TypeError, AttributeError) as error:
        raise HTTPException(502, 'Danh sách models không đúng định dạng; nhập model ID thủ công') from error
    return {'models': models}


@router.post('/api/gateway/select')
def select_model(body: ModelInput, request: Request):
    local_admin(request)
    model = body.model.strip()
    if not model:
        raise HTTPException(422, 'Model ID không được trống')
    form_url = body.base_url.strip().rstrip('/')
    if form_url and form_url == ai_gateway.pending.get('base_url'):
        # Áp dụng gateway vừa bấm "Kiểm tra" (kể cả khi /models lỗi, để nhập model thủ công)
        ai_gateway.gateway.update(ai_gateway.pending)
        ai_gateway.pending.clear()
    elif form_url:
        raise HTTPException(409, 'Bấm "Kiểm tra & tải models" với Base URL này trước, hoặc để trống Base URL để chỉ đổi model')
    elif not ai_gateway.gateway['base_url']:
        raise HTTPException(409, 'Nhập gateway và kiểm tra kết nối trước')
    # Base URL trống: chỉ đổi model của gateway đang dùng (vd từ .env)
    ai_gateway.gateway['model'] = model
    ai_gateway.source = 'ui'  # ghi đè tạm thời; chạy lại service sẽ quay về .env
    return {'model': model}


@router.post('/api/local/experiment')
async def experiment(body: ExperimentInput, request: Request):
    local_admin(request)
    config = {**ai_gateway.gateway, 'model': body.model.strip()}
    diagnostic = {'requests': [], 'raw_responses': [], 'total_tokens': 0}
    started = perf_counter()
    try:
        result = await run_extraction(body, body.prompt, config, diagnostic,
                                      [turn.model_dump() for turn in body.history])
        outcome = {'ok': True, 'http_status': 200, 'result': result}
    except HTTPException as error:
        outcome = {'ok': False, 'http_status': error.status_code, 'error': error.detail,
                   'category': diagnostic.get('failure_stage', 'upstream' if error.status_code == 502 else 'configuration_or_input')}
    return {**outcome, **diagnostic, 'model': body.model, 'mode': body.mode,
            'elapsed_ms': round((perf_counter() - started) * 1000, 2)}
