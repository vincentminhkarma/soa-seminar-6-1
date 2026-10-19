import argparse
import json
from time import perf_counter
import httpx

CASES = [
    ('Standard 2026-10-20 đến 2026-10-22', ['STANDARD', '2026-10-20', '2026-10-22']),
    ('Deluxe từ 20/10/2026 đến 21/10/2026', ['DELUXE', '2026-10-20', '2026-10-21']),
    ('DELUXE 22/10/2026 đến 23/10/2026', ['DELUXE', '2026-10-22', '2026-10-23']),
    ('Suite 2026-10-20 đến 2026-10-21', ['SUITE', '2026-10-20', '2026-10-21']),
    ('Xin chào', [None, None, None]),
    ('Tôi cần phòng Deluxe', ['DELUXE', None, None]),
    ('Phòng tiêu chuẩn từ 20/10/2026 đến 22/10/2026', ['STANDARD', '2026-10-20', '2026-10-22']),
    ('Ngày trả 22/10/2026, ngày nhận 20/10/2026, phòng Deluxe', ['DELUXE', '2026-10-20', '2026-10-22']),
]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['regex', 'openai', 'tools'], default='regex')
    parser.add_argument('--base', default='http://127.0.0.1:8000', help='Địa chỉ service, đổi khi chạy port khác')
    args = parser.parse_args()
    results = []
    with httpx.Client(timeout=180) as client:
        for text, expected in CASES:
            started = perf_counter()
            try:
                response = client.post(args.base.rstrip('/') + '/api/v1/extract-booking', json={'raw_text': text, 'mode': args.mode})
                body = response.json()
                booking = body.get('booking', {})
                actual = [booking.get(key) for key in ('room_type', 'check_in', 'check_out')]
                results.append({'text': text, 'expected': expected, 'http_status': response.status_code,
                    'correct': response.status_code == 200 and actual == expected,
                    'client_ms': round((perf_counter() - started) * 1000, 2), 'response': body})
            except httpx.RequestError as error:
                results.append({'text': text, 'correct': False, 'error': str(error)})
    print(json.dumps({'mode': args.mode, 'correct': sum(row['correct'] for row in results),
                      'count': len(CASES), 'results': results}, ensure_ascii=False, indent=2))
