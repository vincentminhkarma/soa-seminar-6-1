# Tích hợp dịch vụ ngoài: gọi gateway AI tương thích OpenAI (GET /models, POST /chat/completions).
import ipaddress
import socket
from secrets import token_urlsafe
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from app.config import GATEWAY_API_KEY, GATEWAY_BASE_URL, GATEWAY_MODEL, GATEWAY_TIMEOUT_SECONDS, TEMPERATURE
from app.schemas import GatewayInput

gateway = {'base_url': '', 'api_key': '', 'model': ''}  # cấu hình đang dùng, chỉ nằm trong RAM, không trả key về client
pending = {}  # gateway vừa nhập ở nút "Kiểm tra"; chỉ áp dụng khi bấm "Sử dụng model"
source = ''   # cấu hình đang dùng đến từ đâu: 'env' (file .env) hoặc 'ui' (giao diện, tạm thời)
ADMIN_TOKEN = token_urlsafe(32)  # đổi mỗi lần khởi động; giao diện local dùng để cấu hình gateway


def load_gateway(base_url, api_key, model):
    global source
    if not (base_url or api_key):
        return  # .env trống: chỉ regex, cấu hình gateway trên giao diện
    checked = GatewayInput(base_url=base_url, api_key=api_key)  # cùng kiểm tra như nhập trên giao diện
    gateway.update(base_url=checked.base_url, api_key=checked.api_key, model=model)
    source = 'env'


load_gateway(GATEWAY_BASE_URL, GATEWAY_API_KEY, GATEWAY_MODEL)


async def gateway_request(config, path, payload=None):
    hostname = urlsplit(config['base_url']).hostname
    try:
        addresses = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise HTTPException(422, 'Gateway phải có địa chỉ IP công khai')
        async with httpx.AsyncClient(timeout=GATEWAY_TIMEOUT_SECONDS, follow_redirects=False, trust_env=False) as client:
            response = await client.request('POST' if payload is not None else 'GET',
                config['base_url'] + path, headers={'Authorization': 'Bearer ' + config['api_key']}, json=payload)
        if response.status_code != 200:
            raise HTTPException(502, f'Gateway HTTP {response.status_code}; kiểm tra key/quota/model')
        return response.json()
    except (httpx.RequestError, OSError, ValueError) as error:
        raise HTTPException(502, 'Không kết nối được gateway hoặc JSON không hợp lệ') from error


async def chat(messages, config_override=None, **options):
    config = dict(config_override or gateway)
    if config['base_url']:
        if not config['model']:
            raise HTTPException(503, 'Chưa chọn model gateway')
        return await gateway_request(config, '/chat/completions', payload={
            'model': config['model'], 'messages': messages, 'temperature': TEMPERATURE, **options})
    raise HTTPException(503, 'Chưa cấu hình gateway và chọn model trên giao diện local')
