# Điểm vào của AI Booking Service: tạo app FastAPI, gắn router, chạy server.
# Chạy từ thư mục gốc dự án:  python -m app.main
from fastapi import FastAPI

from app.config import HOST, PORT
from app.routers import booking, gateway

app = FastAPI(title='SOA Seminar: AI Booking Service', version='2.0')
app.include_router(booking.router)
app.include_router(gateway.router)


if __name__ == '__main__':
    import uvicorn
    # proxy_headers=False: không tin địa chỉ client do proxy/ngrok khai báo
    uvicorn.run(app, host=HOST, port=PORT, proxy_headers=False)
