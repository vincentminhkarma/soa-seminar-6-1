# Hợp đồng chính của service: consumer chỉ cần biết URL và JSON này.
from fastapi import APIRouter, HTTPException, Request

from app.dependencies import is_local
from app.schemas import Input
from app.services.extraction import run_extraction

router = APIRouter(tags=['booking'])


@router.post('/api/v1/extract-booking')
async def extract(request: Input, http_request: Request):
    if request.mode != 'regex' and not is_local(http_request):
        raise HTTPException(403, 'Demo có phí chỉ cho phép gọi local; tunnel dùng regex')  # bảo vệ key và chi phí
    return await run_extraction(request)
