# Hướng dẫn cài đặt và chạy AI Booking Service

Tài liệu đi từng bước, từ một máy chưa cài gì đến lúc gọi được service. Mỗi bước có phần **Kết quả mong đợi** để tự đối chiếu trước khi sang bước sau.

- Bước 1–7 không cần API key và không tốn phí.
- Bước 8 (bật AI) và bước 9 (ngrok) là tùy chọn.

Mỗi lệnh có hai phiên bản: **macOS / Linux** dùng Terminal, **Windows** dùng PowerShell.

## Cách nhanh: một lệnh

Sau khi làm xong bước 1 (cài Python, Git) và bước 2 (tải mã nguồn), chạy một lệnh từ thư mục dự án:

```bash
bash start.sh       # macOS / Linux
```

```powershell
.\start.bat         # Windows (hoặc nhấp đúp start.bat trong File Explorer)
```

Script tự làm bước 3 và bước 4, chạy kiểm thử, rồi mở Swagger. Bạn tiếp tục từ bước 5.

Thêm `--setup-only` nếu chỉ muốn cài mà chưa chạy service, hoặc `--no-open` để không mở trình duyệt.

Các bước dưới đây mô tả từng việc script làm, dùng khi muốn làm tay hoặc khi script báo lỗi.

## Mục lục

1. [Chuẩn bị công cụ](#1-chuẩn-bị-công-cụ)
2. [Tải mã nguồn](#2-tải-mã-nguồn)
3. [Tạo môi trường ảo và cài thư viện](#3-tạo-môi-trường-ảo-và-cài-thư-viện)
4. [Chạy service](#4-chạy-service)
5. [Gửi request đầu tiên qua Swagger](#5-gửi-request-đầu-tiên-qua-swagger)
6. [Chạy kiểm thử và thực nghiệm](#6-chạy-kiểm-thử-và-thực-nghiệm)
7. [Gọi service từ consumer khác](#7-gọi-service-từ-consumer-khác)
8. [Bật AI (chế độ openai và tools)](#8-bật-ai-chế-độ-openai-và-tools)
9. [Cho máy khác gọi qua ngrok](#9-cho-máy-khác-gọi-qua-ngrok)
10. [Dừng service](#10-dừng-service)
11. [Xử lý lỗi thường gặp](#11-xử-lý-lỗi-thường-gặp)

## 1. Chuẩn bị công cụ

Cần **Python 3.11 trở lên** và **Git**:

- **Python:** tải ở https://www.python.org/downloads/. Trên Windows, ở màn hình đầu tiên của bộ cài nhớ tích **Add python.exe to PATH**.
- **Git:** tải ở https://git-scm.com/downloads.
- **VS Code (không bắt buộc):** nếu dùng, cài thêm extension **REST Client** (`humao.rest-client`) để chạy file `client/demo.http`.

Cài xong, mở một terminal **mới** và kiểm tra:

```bash
# macOS / Linux
python3 --version
git --version
```

```powershell
# Windows
py --version
git --version
```

**Kết quả mong đợi:** hiện `Python 3.11` trở lên (3.12, 3.13… đều được) và một phiên bản Git.

## 2. Tải mã nguồn

```bash
git clone https://github.com/vincentminhkarma/soa-seminar-6-1.git
cd soa-seminar-6-1
```

Không dùng Git cũng được:

1. Trên trang GitHub, bấm **Code → Download ZIP**.
2. Giải nén.
3. Mở terminal tại thư mục vừa giải nén.

**Mọi lệnh từ đây trở đi đều chạy trong thư mục này.**

**Kết quả mong đợi:** lệnh `ls` (macOS/Linux) hoặc `dir` (Windows) liệt kê được `app`, `client`, `docs`, `slide`, `tests` và `requirements.txt`.

## 3. Tạo môi trường ảo và cài thư viện

Nếu đã chạy `start.sh` / `start.bat` thì bỏ qua bước 3 và bước 4.

Môi trường ảo `.venv` giữ thư viện riêng cho dự án, không ảnh hưởng tới Python của máy.

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

```powershell
# Windows
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Trên Windows, các lệnh gọi thẳng `.\.venv\Scripts\python.exe` nên không cần bước Activate, và không bị Execution Policy chặn.

**Kết quả mong đợi:**

- Có dòng `Successfully installed` kèm fastapi, uvicorn, pydantic, httpx, python-dotenv.
- Trên macOS/Linux, đầu dòng lệnh hiện `(.venv)`.

## 4. Chạy service

```bash
# macOS / Linux
python -m app.main
```

```powershell
# Windows
.\.venv\Scripts\python.exe -m app.main
```

**Kết quả mong đợi:** terminal in `Uvicorn running on http://127.0.0.1:8000`.

Giữ nguyên terminal này trong suốt quá trình dùng, vì tắt nó là service dừng. Các bước sau mở thêm terminal thứ hai.

**Khi sửa code**, chạy kèm `--reload`: mỗi lần lưu file `.py` trong `app/`, service tự khởi động lại.

```bash
python -m app.main --reload
```

Không nên dùng `--reload` khi demo, vì mỗi lần service khởi động lại sẽ:

- mất cấu hình đã nhập trên giao diện (quay về `.env`);
- đổi token local, nên phải tải lại trang http://127.0.0.1:8000.

Sửa `app/static/ui.html` thì không cần reload, chỉ cần tải lại trang trên trình duyệt. Sửa `.env` thì phải tự chạy lại service.

## 5. Gửi request đầu tiên qua Swagger

1. Mở http://127.0.0.1:8000/docs.
2. Chọn **POST /api/v1/extract-booking** → **Try it out**.
3. Dán nội dung sau vào ô Request body, rồi bấm **Execute**:

   ```json
   {"raw_text": "Standard từ 20/10/2026 đến 22/10/2026", "mode": "regex"}
   ```

**Kết quả mong đợi:** Code `200`, `"status": "EXTRACTED"`, `"check_in": "2026-10-20"`.

Tiếp theo, sửa body rồi Execute lại. Hãy đoán kết quả trước khi bấm:

| Thay đổi | Kết quả |
|---|---|
| `"raw_text": "Xin chào"` | 200, `NEED_MORE_INFO`, ba trường `null` |
| `"raw_text": "Deluxe từ 22/10/2026 đến 20/10/2026"` | 422, ngày trả trước ngày nhận |
| `"mode": "magic"` | 422, mode ngoài `regex`, `openai`, `tools` |
| `"mode": "openai"` (chưa cấu hình AI) | 503, chưa cấu hình gateway |

## 6. Chạy kiểm thử và thực nghiệm

Mở **terminal thứ hai** và `cd` vào thư mục dự án. Trên macOS/Linux, kích hoạt lại môi trường ảo trước.

```bash
# macOS / Linux
source .venv/bin/activate
python -m unittest -v
python client/experiment.py --mode regex
```

```powershell
# Windows
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe client\experiment.py --mode regex
```

**Kết quả mong đợi:**

- `unittest` in `Ran 10 tests ... OK`. Các test này chạy offline và giả lập AI nên không tốn phí.
- `experiment.py` gửi 8 tin nhắn mẫu tới service đang chạy, rồi in `"correct": 6` trên `"count": 8`. Regex trượt câu "Phòng tiêu chuẩn…" và câu đảo thứ tự ngày; đây là giới hạn có chủ đích để so sánh với AI.

Lưu kết quả ra file nếu cần: `python client/experiment.py --mode regex > regex-results.json`.

## 7. Gọi service từ consumer khác

Service chỉ giao tiếp qua HTTP, nên consumer viết bằng ngôn ngữ nào cũng gọi được mà không cần import code Python. Chọn một trong bốn cách sau.

**Terminal (macOS / Linux):**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/extract-booking -H 'Content-Type: application/json' -d '{"raw_text":"Suite từ 25/10/2026 đến 27/10/2026","mode":"regex"}'
```

**PowerShell:**

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/extract-booking -ContentType 'application/json' -Body '{"raw_text":"Suite 2026-10-25 den 2026-10-27","mode":"regex"}'
```

**Trình duyệt, không cần cài gì:**

1. Trên trang http://127.0.0.1:8000/docs, nhấn F12 → Console.
2. Chrome có thể yêu cầu gõ `allow pasting` trước khi cho dán.
3. Dán đoạn sau rồi Enter:

```js
const r = await fetch('/api/v1/extract-booking', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({raw_text: 'Suite từ 25/10/2026 đến 27/10/2026', mode: 'regex'})
});
console.log(r.status, await r.json());
```

**VS Code REST Client:**

1. Mở `client/demo.http`.
2. Bấm **Send Request** phía trên từng khối:
   - Khối **A, B** chạy được ngay, không tốn phí.
   - Khối **C** và **D5–D6** cần token local, lấy theo hướng dẫn ở đầu file.
   - Khối **D** gọi AI (có phí).
   - Khối **E** cần ngrok (bước 9).

**Kết quả mong đợi:** nhận `"room_type": "SUITE"`, `"check_in": "2026-10-25"`, `"check_out": "2026-10-27"`, `"status": "EXTRACTED"`.

## 8. Bật AI (chế độ openai và tools)

Bước này cần một gateway tương thích OpenAI. Gateway phải có Base URL **HTTPS công khai** và **không** được là localhost hay IP nội bộ. Mỗi lần gọi tính phí theo token, nên chỉ chạy khi chủ key đồng ý.

Có hai cách cấu hình:

### Cách A: file .env (cấu hình một lần, không phải gõ key mỗi lần chạy)

**1. Có file `.env` ở thư mục gốc.**

`start.sh` / `start.bat` tự tạo file này (để trống) ở lần chạy đầu. Nếu làm tay, tạo bằng lệnh dưới; lệnh **không ghi đè** file đã có:

```bash
# macOS / Linux
[ -f .env ] || printf '# Cau hinh gateway AI\nGATEWAY_BASE_URL=\nGATEWAY_API_KEY=\nGATEWAY_MODEL=\n' > .env
```

```powershell
# Windows
if (!(Test-Path .env)) { Set-Content .env "# Cau hinh gateway AI`nGATEWAY_BASE_URL=`nGATEWAY_API_KEY=`nGATEWAY_MODEL=" }
```

**2. Mở `.env`.**

Dự án cấu hình VS Code ẩn `.env` khỏi Explorer, để key không lộ khi chia sẻ màn hình. Vì vậy hãy mở bằng lệnh:

| Hệ điều hành | Lệnh |
|---|---|
| macOS | `open -e .env` (TextEdit), hoặc `code .env` nếu đã cài lệnh `code` |
| Windows | `notepad .env` |
| Linux | `nano .env` |

**3. Chọn gateway và lấy API key.**

Base URL phải là HTTPS công khai. Service tự nối thêm `/models` và `/chat/completions` vào sau địa chỉ này.

| Nhà cung cấp | `GATEWAY_BASE_URL` | Lấy key ở |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | https://platform.openai.com/api-keys (cần nạp credit API; gói ChatGPT không kèm quota API) |
| OpenRouter | `https://openrouter.ai/api/v1` | https://openrouter.ai/settings/keys |
| Groq | `https://api.groq.com/openai/v1` | https://console.groq.com/keys |

Gateway khác cũng dùng được nếu tương thích OpenAI, nghĩa là có `GET /models` và `POST /chat/completions`.

Code được viết theo chuẩn OpenAI Chat Completions, có dùng JSON mode và tools. Không phải model nào cũng hỗ trợ đủ hai tính năng này, nên luôn thử `mode: tools` trước buổi demo.

**4. Điền URL và key, để trống model.** Ví dụ:

```text
GATEWAY_BASE_URL=https://api.openai.com/v1
GATEWAY_API_KEY=sk-...dán-nguyên-key...
GATEWAY_MODEL=
```

Quy tắc điền:

- Mỗi biến nằm trên một dòng.
- Viết ngay sau dấu `=`, không có dấu cách.
- Không bọc giá trị trong dấu nháy.
- Không xuống dòng giữa chừng key.

**5. Lấy model ID.** Lưu file, rồi chạy:

```bash
bash start.sh --models        # macOS / Linux
```

```powershell
.\start.bat --models          # Windows
```

Lệnh in danh sách model mà key của bạn dùng được. Lệnh **không** in key ra màn hình.

Chép một ID trong danh sách vào `GATEWAY_MODEL=`, rồi lưu file.

Nếu lệnh báo `HTTP 401`, key sai hoặc đã bị thu hồi. Nếu báo `Không kết nối được`, Base URL sai hoặc máy mất mạng.

**6. Chạy lại service** bằng `bash start.sh` (Windows: `.\start.bat`).

**Kết quả mong đợi:** góc trên phải trang http://127.0.0.1:8000 hiện `<model> · từ .env`.

Nếu URL không phải HTTPS công khai, hoặc đã điền URL mà thiếu key, script sẽ dừng ở bước kiểm thử và báo tên trường sai (`base_url` hoặc `api_key`).

`.env` đã có trong `.gitignore` nên không bị đẩy lên GitHub. Đừng gửi file này cho người khác, và đừng mở nó khi đang chia sẻ màn hình.

### Cách B: nhập trên giao diện (key chỉ giữ trong RAM, mất khi tắt service)

1. Mở http://127.0.0.1:8000 trên chính máy chạy service.
2. Nhập **Base URL** và **API key** → bấm **Kiểm tra & tải models**.
3. Chọn model trong danh sách, hoặc gõ vào ô **Model ID thủ công** → bấm **Sử dụng model**.

Cách hai nút hoạt động:

- **Kiểm tra & tải models** chỉ thử kết nối, **chưa** đổi cấu hình đang dùng. Gõ sai URL hoặc key thì cấu hình từ `.env` vẫn chạy bình thường.
- **Sử dụng model** mới áp dụng gateway đang có trong ô Base URL. Nếu `/models` lỗi, bạn vẫn có thể gõ model ID thủ công và bấm nút này.
- **Đã cấu hình bằng `.env` và chỉ muốn đổi model:** để trống ô Base URL, gõ Model ID, rồi bấm **Sử dụng model**. Không cần nhập lại key.
- **Mọi thay đổi trên giao diện chỉ là tạm thời.** Chạy lại service sẽ quay về giá trị trong `.env`.

### Thử AI

Gửi lại request ở bước 5 với `"mode": "openai"` hoặc `"mode": "tools"`.

| Tin nhắn (`mode: tools`) | Kết quả từ backend |
|---|---|
| `Deluxe từ 22/10/2026 đến 23/10/2026` | `"available": true`, có `tool_trace` và `reply` |
| `Deluxe từ 20/10/2026 đến 21/10/2026` | `"available": false` (hết phòng) |
| `Tôi cần phòng Suite` | `NEED_MORE_INFO`, dừng sau lượt 1, không tra tồn kho |

Hai trường cần đọc khi kiểm tra kết quả:

- `availability` và `tool_trace` là kết quả do backend tính, đáng tin cậy.
- `reply` chỉ là câu trả lời do AI diễn đạt lại.

`total_tokens` cộng số token của các lượt gọi thành công.

## 9. Cho máy khác gọi qua ngrok

**1. Chuẩn bị ngrok:**

- Tạo tài khoản miễn phí ở https://ngrok.com.
- Cài ngrok CLI từ https://ngrok.com/download. macOS có thể dùng `brew install ngrok`.
- Lấy **authtoken** trong mục **Your Authtoken** của dashboard ngrok. Đây là token của ngrok, không phải API key AI.

**2. Khai báo authtoken** (chỉ cần một lần):

```bash
ngrok config add-authtoken <AUTHTOKEN_CUA_BAN>
```

**3. Mở đường hầm.** Giữ terminal service đang chạy, mở terminal khác và chạy:

```bash
ngrok http 8000
```

**4. Gọi thử từ máy khác:**

1. Chép địa chỉ `https://…` ở dòng **Forwarding**.
2. Mở địa chỉ đó thêm `/docs` trên điện thoại dùng 4G hoặc máy khác.
3. Gặp trang cảnh báo của ngrok thì bấm **Visit Site**.

**Kết quả mong đợi:**

- Request `mode: regex` trả đúng JSON như khi chạy trên máy.
- Request `mode: openai` hoặc `tools` qua tunnel nhận `403`. Đây là chặn có chủ đích, vì endpoint chưa có xác thực và cần bảo vệ key cùng chi phí.

Nếu dùng `client/demo.http`, hãy dán địa chỉ Forwarding vào dòng `@tunnel` rồi chạy các khối E.

## 10. Dừng service

1. Nhấn Ctrl+C ở terminal ngrok (nếu có).
2. Nhấn Ctrl+C ở terminal service.
3. Trên macOS/Linux, gõ `deactivate` để thoát môi trường ảo.

## 11. Xử lý lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `permission denied: ./start.sh` | Chạy bằng `bash start.sh` thay vì `./start.sh` |
| Windows hiện cảnh báo bảo mật khi mở `start.bat` tải từ ZIP | Chọn chạy tiếp, hoặc mở PowerShell trong thư mục dự án rồi gõ `.\start.bat` |
| Script báo `Cổng 8000 đang được dùng` | Service đã chạy ở cửa sổ khác: tắt nó (Ctrl+C), hoặc đổi `PORT` trong `app/config.py` |
| Script báo `Không tạo được .venv` trên Ubuntu/Debian | Chạy `sudo apt install python3-venv`, rồi chạy lại script |
| `python3` / `py` không được nhận ra | Python chưa cài hoặc chưa có trong PATH. Cài lại (Windows tích **Add python.exe to PATH**), rồi mở terminal mới |
| macOS báo `xcrun: error: invalid active developer path` khi gõ git | Chạy `xcode-select --install`, chờ cài xong rồi gõ lại |
| `Could not open requirements file` | Đang đứng sai thư mục; `cd` vào `soa-seminar-6-1` |
| `No module named app` | Phải chạy `python -m app.main` từ thư mục gốc (nơi thấy thư mục `app`), không chạy từ bên trong `app/` |
| `No module named fastapi` / `uvicorn` / `dotenv` | Đang dùng Python ngoài môi trường ảo. macOS/Linux: `source .venv/bin/activate`. Windows: gọi `.\.venv\Scripts\python.exe` |
| `address already in use` (cổng 8000 bận) | Đổi `PORT = 8001` trong `app/config.py`, mở `http://127.0.0.1:8001/docs`, chạy thực nghiệm kèm `--base http://127.0.0.1:8001`, ngrok dùng `ngrok http 8001` |
| Service dừng ngay khi khởi động, báo `validation error ... base_url` hoặc `api_key` | Giá trị trong `.env` sai: URL phải là HTTPS công khai; nếu đã điền URL thì phải có key. Sửa `.env` hoặc xoá hết giá trị để chạy chỉ regex |
| 503 khi gọi `openai` / `tools` | Chưa cấu hình gateway hoặc chưa chọn model (bước 8) |
| 502 khi gọi `openai` / `tools` | Gateway từ chối hoặc không kết nối được. Kiểm tra key, quota, model ID và mạng |
| 403 khi gọi AI | Đang gọi qua ngrok hoặc từ máy khác; AI chỉ cho gọi trên máy chạy service |
| ngrok báo lỗi authtoken | Kiểm tra lại authtoken của ngrok, đừng dùng API key AI |
