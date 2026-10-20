# Điểm vào của AI Booking Service: tạo app FastAPI, gắn router, chạy server.
# Chạy từ thư mục gốc dự án:  python -m app.main
# Khi sửa code:               python -m app.main --reload   (tự chạy lại khi lưu file .py trong app/ hoặc .env)
import os
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.dependencies import is_local
from app.services import ai_gateway

from app.config import ENV_FILE, HOST, PORT
from app.routers import booking, gateway

app = FastAPI(title='SOA Seminar: AI Booking Service', version='2.0', docs_url=None)
app.include_router(booking.router)
app.include_router(gateway.router)


@app.get('/docs', include_in_schema=False)
def swagger_docs(request: Request):
    page = get_swagger_ui_html(openapi_url=app.openapi_url, title=app.title + ' - Swagger UI').body.decode()
    if is_local(request):
        # Chỉ gửi token cho API quản trị cùng origin, không cho request tới server ngoài.
        interceptor = '''requestInterceptor: (req) => {
            const url = new URL(req.url, window.location.href);
            if (url.origin === window.location.origin &&
                ['/api/gateway/models', '/api/gateway/select', '/api/local/experiment'].includes(url.pathname)) {
                req.headers['x-gateway-token'] = '__TOKEN__';
            }
            return req;
        },'''.replace('__TOKEN__', ai_gateway.ADMIN_TOKEN)
        page = page.replace('const ui = SwaggerUIBundle({', 'const ui = SwaggerUIBundle({\n' + interceptor)
    return HTMLResponse(page, headers={'Cache-Control': 'no-store', 'X-Frame-Options': 'DENY'})


def touch_on_change(watched, target, interval=0.5):
    """uvicorn --reload chỉ theo dõi file .py trong app/; .env nằm ngoài nên khi .env đổi thì chạm target để reload."""
    def mtime():
        try:
            return watched.stat().st_mtime
        except OSError:
            return None
    last = mtime()
    while True:
        time.sleep(interval)
        now = mtime()
        if now != last:
            last = now
            os.utime(target)


if __name__ == '__main__':
    import uvicorn
    reload = '--reload' in sys.argv[1:]  # chỉ dùng khi sửa code; reload làm mất cấu hình nhập trên giao diện
    if reload:
        threading.Thread(target=touch_on_change, args=(ENV_FILE, Path(__file__).parent / 'config.py'), daemon=True).start()
    # proxy_headers=False: không tin địa chỉ client do proxy/ngrok khai báo
    uvicorn.run('app.main:app' if reload else app, host=HOST, port=PORT, proxy_headers=False,
                reload=reload, reload_dirs=[str(Path(__file__).parent)] if reload else None)
