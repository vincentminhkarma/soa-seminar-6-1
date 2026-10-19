#!/bin/sh
# Cài đặt và chạy AI Booking Service trên macOS / Linux:  bash start.sh
# Tùy chọn: --setup-only (chỉ cài đặt, không chạy), --no-open (không mở trình duyệt),
#           --models (in danh sách model của gateway trong .env)
cd "$(dirname "$0")" || exit 1
for py in python3 python3.14 python3.13 python3.12 python3.11; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    exec "$py" start.py "$@"
  fi
done
echo "[LỖI] Cần Python 3.11 trở lên. Tải ở https://www.python.org/downloads/ rồi mở terminal mới." >&2
exit 1
