# Hợp đồng chính của service: consumer chỉ cần biết URL và JSON này.
from fastapi import APIRouter, HTTPException, Request

from app.config import PUBLIC_AI_LIMIT
from app.dependencies import is_local
from app.schemas import Input
from app.services import ai_gateway
from app.services.extraction import run_extraction

router = APIRouter(tags=['booking'])


@router.post('/api/v1/extract-booking')
async def extract(request: Input, http_request: Request):
    if request.mode != 'regex' and not is_local(http_request):  # bảo vệ key và chi phí
        if not PUBLIC_AI_LIMIT:
            raise HTTPException(403, 'Demo có phí chỉ cho phép gọi local; tunnel dùng regex')
        if ai_gateway.public_used >= PUBLIC_AI_LIMIT:
            raise HTTPException(429, f'Đã dùng hết {PUBLIC_AI_LIMIT} lượt AI công khai; tunnel dùng regex')
        ai_gateway.public_used += 1  # hạn mức chung cho mọi khách, không chia theo người
    return await run_extraction(request)
