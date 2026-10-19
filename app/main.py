# Điểm vào của AI Booking Service: tạo app FastAPI, gắn router, chạy server.
# Chạy từ thư mục gốc dự án:  python -m app.main
# Khi sửa code:               python -m app.main --reload   (tự chạy lại khi lưu file .py trong app/)
import sys
from pathlib import Path

from fastapi import FastAPI

from app.config import HOST, PORT
from app.routers import booking, gateway

app = FastAPI(title='SOA Seminar: AI Booking Service', version='2.0')
app.include_router(booking.router)
app.include_router(gateway.router)


if __name__ == '__main__':
    import uvicorn
    reload = '--reload' in sys.argv[1:]  # chỉ dùng khi sửa code; reload làm mất cấu hình nhập trên giao diện
    # proxy_headers=False: không tin địa chỉ client do proxy/ngrok khai báo
    uvicorn.run('app.main:app' if reload else app, host=HOST, port=PORT, proxy_headers=False,
                reload=reload, reload_dirs=[str(Path(__file__).parent)] if reload else None)
