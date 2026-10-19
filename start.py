"""Cài đặt và chạy AI Booking Service bằng một lệnh.

macOS / Linux:  bash start.sh          Windows:  nhấp đúp start.bat (hoặc .\\start.bat)
Chạy trực tiếp: python3 start.py       (Windows: py start.py)

Lần đầu: tạo .venv, cài thư viện, chạy kiểm thử, khởi động service, mở Swagger.
Các lần sau bỏ qua phần đã làm nên chỉ mất vài giây.
Chỉ dùng thư viện chuẩn của Python vì lúc chạy file này chưa có thư viện nào được cài.
"""
import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / '.venv'
VPY = VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
STAMP = VENV / '.requirements.sha256'  # requirements.txt đã cài; đổi file này thì cài lại
ENV_FILE = ROOT / '.env'
ENV_TEMPLATE = ('# Cau hinh gateway AI cho che do openai/tools. De trong: service chi chay regex.\n'
                'GATEWAY_BASE_URL=\nGATEWAY_API_KEY=\nGATEWAY_MODEL=\n')
# Chạy trong .venv: đọc URL/key từ .env, in danh sách model; không bao giờ in key hay nội dung lỗi của gateway
LIST_MODELS = '''
import httpx
from app.config import GATEWAY_BASE_URL as url, GATEWAY_API_KEY as key
if not (url and key):
    raise SystemExit('[LỖI] Chưa điền GATEWAY_BASE_URL và GATEWAY_API_KEY trong .env')
try:
    r = httpx.get(url.rstrip('/') + '/models', headers={'Authorization': 'Bearer ' + key}, timeout=30)
except httpx.HTTPError:
    raise SystemExit('[LỖI] Không kết nối được ' + url + ' - kiểm tra Base URL và mạng')
if r.status_code != 200:
    raise SystemExit('[LỖI] Gateway trả HTTP %d - kiểm tra Base URL và API key' % r.status_code)
ids = sorted(m['id'] for m in r.json().get('data', []) if isinstance(m.get('id'), str))
print('\\n'.join(ids) if ids else 'Gateway không trả danh sách model; hỏi nhà cung cấp model ID.')
'''


def step(text):
    print('\n==> ' + text, flush=True)


def fail(text):
    print('\n[LỖI] ' + text, file=sys.stderr, flush=True)
    sys.exit(1)


def venv_run(*args):
    return subprocess.run([str(VPY)] + list(args), cwd=ROOT).returncode == 0


def wait_until_up(url, server, seconds=20):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # bỏ qua proxy hệ thống
    deadline = time.time() + seconds
    while time.time() < deadline and server.poll() is None:
        try:
            opener.open(url, timeout=1)
            return True
        except OSError:
            time.sleep(0.3)
    return False


def main():
    if sys.version_info < (3, 11):
        fail('Cần Python 3.11 trở lên, máy đang chạy Python %d.%d. '
             'Tải ở https://www.python.org/downloads/ rồi mở terminal mới.' % sys.version_info[:2])
    parser = argparse.ArgumentParser(description='Cài đặt và chạy AI Booking Service.')
    parser.add_argument('--setup-only', action='store_true', help='chỉ cài đặt và kiểm thử, không chạy service')
    parser.add_argument('--no-open', action='store_true', help='không tự mở trình duyệt')
    parser.add_argument('--models', action='store_true', help='in danh sách model của gateway khai báo trong .env rồi thoát')
    args = parser.parse_args()

    step('1/4  Môi trường ảo .venv')
    if VPY.exists():
        print('Đã có, dùng lại.')
    else:
        # Gọi đúng lệnh "python -m venv" như làm tay; venv.create() mặc định chép file python và hỏng với vài bản cài
        if subprocess.run([sys.executable, '-m', 'venv', '--clear', str(VENV)]).returncode != 0:
            shutil.rmtree(VENV, ignore_errors=True)
            fail('Không tạo được .venv, xem thông báo phía trên. Ubuntu/Debian: sudo apt install python3-venv rồi chạy lại.')
        print('Đã tạo .venv.')
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_TEMPLATE, encoding='utf-8')
        print('Đã tạo file .env trống. Muốn bật AI: điền 3 biến trong .env rồi chạy lại.')

    step('2/4  Thư viện trong requirements.txt')
    digest = hashlib.sha256((ROOT / 'requirements.txt').read_bytes()).hexdigest()
    if STAMP.exists() and STAMP.read_text() == digest:
        print('Đã cài đủ, bỏ qua.')
    else:
        print('Lần đầu mất khoảng 1 phút và cần Internet...', flush=True)
        if not venv_run('-m', 'pip', 'install', '--disable-pip-version-check', '-r', 'requirements.txt'):
            fail('Cài thư viện thất bại. Kiểm tra mạng rồi chạy lại.')
        STAMP.write_text(digest)

    if args.models:
        step('Danh sách model của gateway trong .env')
        sys.exit(0 if venv_run('-c', LIST_MODELS) else 1)

    step('3/4  Kiểm thử')
    if not venv_run('-m', 'unittest', '-q'):
        fail('Có test lỗi, xem thông báo phía trên. Nếu lỗi nhắc base_url hoặc api_key: '
             'sửa giá trị trong .env, hoặc xoá hết giá trị để chỉ chạy regex.')

    if args.setup_only:
        print('\nCài đặt xong. Chạy service: bash start.sh (Windows: start.bat)')
        return

    step('4/4  Chạy service')
    host, port = subprocess.run([str(VPY), '-c', 'from app.config import HOST, PORT; print(HOST, PORT)'],
                                cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    with socket.socket() as probe:
        if probe.connect_ex((host, int(port))) == 0:
            fail('Cổng %s đang được dùng, có thể service đã chạy ở cửa sổ khác. '
                 'Tắt chương trình đó, hoặc đổi PORT trong app/config.py.' % port)
    url = 'http://%s:%s' % (host, port)
    server = subprocess.Popen([str(VPY), '-m', 'app.main'], cwd=ROOT)
    try:
        if wait_until_up(url + '/docs', server):
            print('\nSwagger:   %s/docs\nGiao diện: %s\nNhấn Ctrl+C để dừng.\n' % (url, url), flush=True)
            if not args.no_open:
                webbrowser.open(url + '/docs')
        server.wait()
    except KeyboardInterrupt:
        server.wait()
        print('\nĐã dừng service.')
        return
    if server.returncode != 0:
        fail('Service dừng do lỗi, xem thông báo phía trên.')


if __name__ == '__main__':
    main()
