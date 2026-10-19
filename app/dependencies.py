# Kiểm tra request đến từ đâu: AI và cấu hình gateway chỉ cho máy local, không cho qua ngrok/proxy.
from fastapi import HTTPException, Request

from app.services import ai_gateway

LOCAL_HOSTS = ('127.0.0.1', '::1')


def is_local(request: Request):
    forwarded = request.headers.get('x-forwarded-for') or request.headers.get('forwarded')
    return bool(request.client and request.client.host in LOCAL_HOSTS and not forwarded)


def local_admin(request: Request):
    if not request.client or request.client.host not in LOCAL_HOSTS:
        raise HTTPException(403, 'Cấu hình gateway chỉ trên máy local')
    if request.headers.get('x-gateway-token') != ai_gateway.ADMIN_TOKEN:
        raise HTTPException(403, 'Thiếu token cấu hình local')
    if request.headers.get('x-forwarded-for') or request.headers.get('forwarded'):
        raise HTTPException(403, 'Không cấu hình qua tunnel/proxy')
