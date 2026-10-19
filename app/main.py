# Điểm vào của AI Booking Service: tạo app FastAPI, gắn router, chạy server.
# Chạy từ thư mục gốc dự án:  python -m app.main
# Khi sửa code:               python -m app.main --reload   (tự chạy lại khi lưu file .py trong app/ hoặc .env)
import os
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI

from app.config import ENV_FILE, HOST, PORT
from app.routers import booking, gateway

app = FastAPI(title='SOA Seminar: AI Booking Service', version='2.0')
app.include_router(booking.router)
app.include_router(gateway.router)


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
