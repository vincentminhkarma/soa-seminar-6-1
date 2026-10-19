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
    page = page.replace('__ADMIN_TOKEN__', ai_gateway.ADMIN_TOKEN if local else '').replace('__ACTIVE_MODEL__', model)
    return HTMLResponse(page, headers={'Cache-Control': 'no-store', 'X-Frame-Options': 'DENY'})


@router.post('/api/gateway/models')
async def gateway_models(body: GatewayInput, request: Request):
    local_admin(request)
    config = {'base_url': body.base_url, 'api_key': body.api_key, 'model': ''}
    ai_gateway.gateway.update(config)
    result = await ai_gateway.gateway_request(config, '/models')
    try:
        models = sorted({row['id'] for row in result['data'] if isinstance(row.get('id'), str)})
    except (KeyError, TypeError, AttributeError) as error:
        raise HTTPException(502, 'Danh sách models không đúng định dạng; nhập model ID thủ công') from error
    return {'models': models}


@router.post('/api/gateway/select')
def select_model(body: ModelInput, request: Request):
    local_admin(request)
    if not ai_gateway.gateway['base_url']:
        raise HTTPException(409, 'Nhập gateway và kiểm tra kết nối trước')
    ai_gateway.gateway['model'] = body.model.strip()
    if not ai_gateway.gateway['model']:
        raise HTTPException(422, 'Model ID không được trống')
    return {'model': ai_gateway.gateway['model']}


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
