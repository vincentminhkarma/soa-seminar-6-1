# AI Booking Service · Seminar SOA chủ đề 6-1

Service REST viết bằng FastAPI. Service nhận một tin nhắn đặt phòng viết tự nhiên và trả về JSON có cấu trúc: loại phòng, ngày nhận, ngày trả.

Dự án minh hoạ việc tích hợp OpenAI API vào kiến trúc hướng dịch vụ (SOA):

- Consumer chỉ giao tiếp với service qua hợp đồng HTTP/JSON.
- AI chỉ đưa ra đề xuất; backend kiểm tra và quyết định có chấp nhận hay không.

Cả ba chế độ xử lý dùng chung một endpoint, chọn bằng trường `mode`:

| `mode` | Cách xử lý | Cần API key |
|---|---|---|
| `regex` | Quy tắc cố định, không gọi AI | Không |
| `openai` | Chat Completion trích xuất JSON, Pydantic kiểm tra kết quả | Có |
| `tools` | AI trích xuất → AI đề xuất gọi hàm → backend tra tồn kho giả lập → AI trả lời (tối đa 3 lượt gọi) | Có |

## Yêu cầu

- Python 3.11 trở lên
- Git, hoặc tải ZIP từ GitHub
- Chế độ `openai` và `tools` cần thêm một gateway tương thích OpenAI, gồm Base URL HTTPS, API key và model ID. Chế độ `regex` không cần.

## Cài đặt và chạy bằng một lệnh

Clone repo, rồi chạy script tương ứng với hệ điều hành:

```bash
git clone https://github.com/vincentminhkarma/soa-seminar-6-1.git
cd soa-seminar-6-1
bash start.sh          # macOS / Linux
```

Trên **Windows**: nhấp đúp `start.bat`, hoặc gõ `.\start.bat` trong PowerShell.

Script tự làm hết các bước sau:

1. Tìm Python 3.11+ trên máy.
2. Tạo môi trường ảo `.venv` và file `.env` trống.
3. Cài thư viện.
4. Chạy 12 test.
5. Khởi động service và mở Swagger trên trình duyệt.

Lần đầu mất khoảng 1 phút. Từ lần thứ hai, script bỏ qua phần đã cài nên service lên chỉ sau vài giây. Nhấn Ctrl+C để dừng.

| Tùy chọn | Tác dụng |
|---|---|
| `--setup-only` | Chỉ cài đặt và kiểm thử, không chạy service (hợp để chuẩn bị máy trước buổi học) |
| `--no-open` | Không tự mở trình duyệt |
| `--models` | In danh sách model của gateway khai báo trong `.env` (không in key) |

Ví dụ: `bash start.sh --setup-only` hoặc `.\start.bat --no-open`.

## Cài đặt và chạy từng bước

Làm tay thay cho script, để hiểu từng việc script đang làm.

**macOS / Linux**

```bash
git clone https://github.com/vincentminhkarma/soa-seminar-6-1.git
cd soa-seminar-6-1
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app.main
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/vincentminhkarma/soa-seminar-6-1.git
cd soa-seminar-6-1
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.main
```

Khi terminal in `Uvicorn running on http://127.0.0.1:8000`, mở:

- http://127.0.0.1:8000/docs để xem Swagger UI và gửi request thử
- http://127.0.0.1:8000 để mở giao diện web (cấu hình gateway, thử ba chế độ)

Khi sửa code, chạy `python -m app.main --reload`: service tự khởi động lại mỗi khi lưu file `.py` trong `app/` hoặc file `.env`. Không dùng `--reload` khi demo.

Mọi lệnh đều chạy từ thư mục gốc `soa-seminar-6-1`. Hướng dẫn chi tiết từng bước, kèm cách bật AI, chia sẻ qua ngrok và xử lý lỗi, nằm ở [docs/HUONG_DAN_CAI_DAT.md](docs/HUONG_DAN_CAI_DAT.md).

## Gọi thử API

```bash
curl -X POST http://127.0.0.1:8000/api/v1/extract-booking \
  -H 'Content-Type: application/json' \
  -d '{"raw_text": "Standard từ 20/10/2026 đến 22/10/2026", "mode": "regex"}'
```

```json
{
  "mode": "regex",
  "booking": { "room_type": "STANDARD", "check_in": "2026-10-20", "check_out": "2026-10-22" },
  "status": "EXTRACTED",
  "availability": null,
  "tool_trace": [],
  "reply": null,
  "total_tokens": 0,
  "elapsed_ms": 0.2
}
```

Ý nghĩa `status`:

- `EXTRACTED`: đã đọc đủ cả ba trường.
- `NEED_MORE_INFO`: còn thiếu thông tin; các trường thiếu có giá trị `null`.

Cả hai trạng thái đều **không** có nghĩa là đã đặt phòng: service không tạo booking.

## API

| Phương thức | Đường dẫn | Mô tả |
|---|---|---|
| POST | `/api/v1/extract-booking` | Hợp đồng chính. Body: `raw_text` (1–2000 ký tự), `mode` |
| GET | `/docs`, `/openapi.json` | Swagger UI và đặc tả OpenAPI |
| GET | `/` | Giao diện web |
| POST | `/api/gateway/models`, `/api/gateway/select` | Cấu hình gateway từ giao diện (chỉ máy local, cần token) |
| POST | `/api/local/experiment` | Lab thử prompt và lịch sử chat (chỉ máy local, cần token) |

| Mã | Khi nào |
|---|---|
| 200 | Xử lý xong, trả `EXTRACTED` hoặc `NEED_MORE_INFO` |
| 403 | Cấu hình gateway qua tunnel / từ máy khác, hoặc gọi AI qua tunnel khi `PUBLIC_AI_LIMIT = 0` |
| 405 | Sai phương thức HTTP |
| 422 | Đầu vào sai: văn bản trống, ngày trả trước ngày nhận, `mode` không hợp lệ |
| 429 | Khách qua tunnel đã dùng hết `PUBLIC_AI_LIMIT` lượt AI |
| 502 | Gateway lỗi hoặc AI trả sai định dạng |
| 503 | Chưa cấu hình gateway hoặc model |

## Cấu hình

**Thông tin bí mật** đặt trong file `.env` ở thư mục gốc. File này đã có trong `.gitignore`.

| Biến | Ý nghĩa | Ví dụ |
|---|---|---|
| `GATEWAY_BASE_URL` | Địa chỉ HTTPS công khai của gateway | `https://api.openai.com/v1` |
| `GATEWAY_API_KEY` | API key của gateway | |
| `GATEWAY_MODEL` | Model ID gateway hỗ trợ; xem danh sách bằng `bash start.sh --models` | |

`start.sh` / `start.bat` tạo sẵn `.env` trống ở lần chạy đầu. Khi các giá trị còn trống, service chỉ chạy `regex`. Bạn vẫn có thể nhập gateway trên giao diện web; khi đó key chỉ giữ trong RAM.

Cách mở `.env`, gợi ý Base URL của từng nhà cung cấp và cách lấy model ID: xem [mục 8 của hướng dẫn](docs/HUONG_DAN_CAI_DAT.md#8-bật-ai-chế-độ-openai-và-tools).

**Các thông số khác** nằm trong [`app/config.py`](app/config.py):

- `HOST`, `PORT`
- `PUBLIC_AI_LIMIT`: số lượt `openai`/`tools` cho khách qua ngrok (mặc định `0`, chỉ regex)
- `GATEWAY_TIMEOUT_SECONDS`, `TEMPERATURE`
- `MAX_TEXT_LENGTH`, `MAX_NIGHTS`
- `CAPACITY`, `RESERVATIONS` (tồn kho giả lập)
- `PROMPT`

Sửa xong thì khởi động lại service.

## Kiểm thử

```bash
python -m unittest -v                     # 12 test offline, AI được giả lập, không tốn phí
python client/experiment.py --mode regex  # chấm 8 tin nhắn mẫu qua HTTP (service phải đang chạy)
```

Kết quả mong đợi:

- `Ran 12 tests ... OK`.
- Thực nghiệm in `"correct": 6` trên `"count": 8`. Regex không hiểu cách viết "phòng tiêu chuẩn" và câu đảo thứ tự ngày; đó là giới hạn có chủ đích để so sánh với AI.

## Cấu trúc thư mục

```text
app/
  main.py                  tạo app FastAPI, gắn router, chạy server
  config.py                thông số service, đọc .env
  schemas.py               hợp đồng dữ liệu (Pydantic)
  dependencies.py          chặn AI và cấu hình khi gọi qua tunnel / máy khác
  routers/booking.py       POST /api/v1/extract-booking
  routers/gateway.py       giao diện, cấu hình gateway, lab
  services/extraction.py   regex, AI trích xuất, Function Calling
  services/inventory.py    tồn kho giả lập và định nghĩa tool
  services/ai_gateway.py   gọi gateway tương thích OpenAI
  static/ui.html           giao diện web
tests/test_api.py          kiểm thử
client/                    consumer mẫu, chỉ gọi service qua HTTP
  demo.http                request mẫu cho VS Code REST Client
  experiment.py            chấm 8 tin nhắn mẫu
slide/index.html           bài trình bày, mở bằng trình duyệt
docs/HUONG_DAN_CAI_DAT.md  hướng dẫn chi tiết
start.py                   cài đặt và chạy bằng một lệnh (chỉ dùng thư viện chuẩn)
start.sh, start.bat        gọi start.py trên macOS/Linux và Windows
```

## Giới hạn

- Đây là demo học tập: không có xác thực người dùng, không rate limit (trừ hạn mức AI cho khách qua ngrok), không lưu dữ liệu, không tạo booking thật.
- Tồn kho là dữ liệu giả lập cho tháng 10/2026; mỗi lần tra tối đa 30 đêm.
- Regex chỉ nhận tên phòng `STANDARD`, `DELUXE`, `SUITE` và ngày có đủ năm.
- Khi chia sẻ qua ngrok, mặc định chỉ chế độ `regex` được phép, để bảo vệ key và chi phí. Muốn cho khách thử AI, đặt `PUBLIC_AI_LIMIT` trong `app/config.py` (vd `30`); hết lượt thì nhận `429`. Cấu hình gateway và lab luôn chỉ trên máy chạy service.
- Prompt không phải hàng rào bảo mật tuyệt đối. Backend vẫn kiểm tra mọi đầu ra của AI trước khi dùng.
