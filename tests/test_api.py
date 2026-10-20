import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.routers import booking, gateway as gateway_router
from app.services import ai_gateway, extraction, inventory


class ServiceTests(unittest.TestCase):
    def test_gateway_configuration_blocks_remote_clients(self):
        client = TestClient(app)
        self.assertEqual(client.post('/api/gateway/models', json={'base_url': 'https://gateway.example/v1', 'api_key': 'secret'}).status_code, 403)

    def test_gateway_models_and_chat_use_configured_provider(self):
        async def local_app(scope, receive, send):
            scope['client'] = ('127.0.0.1', 1234)
            await app(scope, receive, send)
        client = TestClient(local_app, headers={'X-Gateway-Token': ai_gateway.ADMIN_TOKEN})
        with patch.object(ai_gateway, 'gateway_request', new_callable=AsyncMock) as upstream:
            upstream.return_value = {'data': [{'id': 'model-demo'}]}
            result = client.post('/api/gateway/models', json={'base_url': 'https://gateway.example/v1/', 'api_key': 'secret'})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['models'], ['model-demo'])
            self.assertNotIn('secret', result.text)
            self.assertEqual(client.post('/api/gateway/select', json={'model': 'model-demo', 'base_url': 'https://gateway.example/v1/'}).status_code, 200)
            upstream.return_value = {'choices': [{'message': {'content': '{"room_type":"STANDARD","check_in":null,"check_out":null}'}}]}
            result = client.post('/api/v1/extract-booking', json={'raw_text': 'Standard', 'mode': 'openai'})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(upstream.call_args.args[1], '/chat/completions')
            self.assertEqual(upstream.call_args.kwargs['payload']['model'], 'model-demo')

    def test_experiment_records_invalid_output_and_isolates_model(self):
        async def local_app(scope, receive, send):
            scope['client'] = ('127.0.0.1', 1234)
            await app(scope, receive, send)
        client = TestClient(local_app, headers={'X-Gateway-Token': ai_gateway.ADMIN_TOKEN})
        body = {'raw_text': 'Standard', 'mode': 'openai', 'model': 'trial-b', 'prompt': 'Return JSON'}
        self.assertEqual(TestClient(app).post('/api/local/experiment', json=body).status_code, 403)
        with patch.dict(ai_gateway.gateway, {'base_url': 'https://gateway.example/v1', 'api_key': 'secret', 'model': 'original'}):
            with patch.object(ai_gateway, 'gateway_request', new_callable=AsyncMock) as upstream:
                upstream.return_value = {'choices': [{'message': {'content': 'not json'}}], 'usage': {'total_tokens': 7}}
                data = client.post('/api/local/experiment', json=body).json()
                self.assertFalse(data['ok'])
                self.assertEqual(data['http_status'], 502)
                self.assertEqual(data['total_tokens'], 7)
                self.assertEqual(data['raw_responses'][0][0]['message']['content'], 'not json')
                self.assertEqual(upstream.call_args.kwargs['payload']['model'], 'trial-b')
                self.assertEqual(upstream.call_args.kwargs['payload']['messages'][0]['content'], 'Return JSON')
                self.assertEqual(data['category'], 'output_validation')
                self.assertEqual(ai_gateway.gateway['model'], 'original')
                self.assertNotIn('secret', str(data))

    def test_lab_trace_history_and_full_tool_flow(self):
        async def local_app(scope, receive, send):
            scope['client'] = ('127.0.0.1', 1234)
            await app(scope, receive, send)
        client = TestClient(local_app, headers={'X-Gateway-Token': ai_gateway.ADMIN_TOKEN})
        booking = '{"room_type":"DELUXE","check_in":"2026-10-22","check_out":"2026-10-23"}'
        tool_call = {'id': 'call_1', 'type': 'function', 'function': {'name': 'check_room_availability', 'arguments': booking}}
        with patch.dict(ai_gateway.gateway, {'base_url': 'https://gateway.example/v1', 'api_key': 'secret', 'model': 'm'}):
            with patch.object(ai_gateway, 'gateway_request', new_callable=AsyncMock) as upstream:
                upstream.side_effect = [{'choices': [{'message': {'content': booking}}]},
                                        {'choices': [{'message': {'role': 'assistant', 'content': None, 'tool_calls': [tool_call]}}]},
                                        {'choices': [{'message': {'content': 'Còn phòng Deluxe.'}}]}]
                data = client.post('/api/local/experiment', json={
                    'raw_text': 'Từ 22/10/2026 đến 23/10/2026', 'mode': 'tools', 'model': 'm', 'prompt': 'Chỉ trả JSON.',
                    'history': [{'role': 'user', 'content': 'Mình muốn Deluxe'}, {'role': 'assistant', 'content': 'Ngày nào ạ?'}]}).json()
        first = upstream.call_args_list[0].kwargs['payload']
        sent = data['requests'][0]['messages']
        self.assertEqual([m['role'] for m in sent], ['system', 'user', 'assistant', 'user'])
        self.assertEqual(sent[0]['content'], 'Chỉ trả JSON.')
        self.assertEqual(first['response_format'], {'type': 'json_object'})
        self.assertTrue(data['ok'], data)
        self.assertEqual(data['result']['availability']['available'], True)
        self.assertEqual(data['result']['reply'], 'Còn phòng Deluxe.')
        self.assertEqual(len(data['requests']), 3)
        self.assertIn('tools', data['requests'][1])
        for step in data['requests'][1:]:
            self.assertNotEqual(step['messages'][0]['content'], 'Chỉ trả JSON.')
        self.assertIn('check_room_availability', data['requests'][1]['messages'][0]['content'])
        self.assertEqual(data['requests'][2]['messages'][-2]['role'], 'tool')

    def test_missing_fields_are_not_invented(self):
        self.assertEqual(extraction.extract_regex('Xin chào').model_dump(), {'room_type': None, 'check_in': None, 'check_out': None})

    def test_vietnamese_dates(self):
        booking = extraction.extract_regex('Deluxe từ 20/10/2026 đến 22/10/2026')
        self.assertEqual(booking.check_in.isoformat(), '2026-10-20')

    def test_overlap_and_checkout_boundary(self):
        self.assertEqual(inventory.check_room_availability('DELUXE', '2026-10-20', '2026-10-21')['available'], False)
        self.assertEqual(inventory.check_room_availability('DELUXE', '2026-10-22', '2026-10-23')['available'], True)

    def test_reversed_dates(self):
        with self.assertRaises(ValueError):
            inventory.check_room_availability('DELUXE', '2026-10-22', '2026-10-20')

    def test_api_contract(self):
        client = TestClient(app)
        response = client.post('/api/v1/extract-booking', json={'raw_text': 'Standard 2026-10-20 đến 2026-10-22'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mode'], 'regex')
        self.assertEqual(client.post('/api/v1/extract-booking', json={'raw_text': '   '}).status_code, 422)

    def test_load_gateway_from_env_values(self):
        with patch.dict(ai_gateway.gateway, {'base_url': '', 'api_key': '', 'model': ''}), patch.object(ai_gateway, 'source', ''):
            ai_gateway.load_gateway('', '', '')
            self.assertEqual((ai_gateway.gateway['base_url'], ai_gateway.source), ('', ''))
            ai_gateway.load_gateway('https://gateway.example/v1/', 'secret', 'm1')
            self.assertEqual(ai_gateway.gateway, {'base_url': 'https://gateway.example/v1', 'api_key': 'secret', 'model': 'm1'})
            self.assertEqual(ai_gateway.source, 'env')
        with self.assertRaises(ValueError):
            ai_gateway.load_gateway('http://localhost:11434/v1', 'secret', 'm1')
        with self.assertRaises(ValueError):
            ai_gateway.load_gateway('https://gateway.example/v1', '', 'm1')

    def test_connect_only_applies_on_select(self):
        async def local_app(scope, receive, send):
            scope['client'] = ('127.0.0.1', 1234)
            await app(scope, receive, send)
        client = TestClient(local_app, headers={'X-Gateway-Token': ai_gateway.ADMIN_TOKEN})
        env = {'base_url': 'https://env.example/v1', 'api_key': 'env-key', 'model': 'env-model'}
        typo = {'base_url': 'https://typo.example/v1', 'api_key': 'wrong-key'}
        with patch.dict(ai_gateway.gateway, env), patch.dict(ai_gateway.pending, {}, clear=True), \
                patch.object(ai_gateway, 'source', 'env'), \
                patch.object(ai_gateway, 'gateway_request', new_callable=AsyncMock) as upstream:
            page = client.get('/').text
            self.assertIn("gatewaySource = 'env'", page)
            self.assertIn("activeModel = 'env-model'", page)
            self.assertNotIn('env-key', page)
            self.assertIn("gatewaySource = ''", TestClient(app).get('/').text)  # máy khác không biết cấu hình
            # Gõ sai trên giao diện: kết nối lỗi, cấu hình từ .env vẫn chạy
            upstream.side_effect = HTTPException(502, 'Gateway HTTP 401; kiểm tra key/quota/model')
            self.assertEqual(client.post('/api/gateway/models', json=typo).status_code, 502)
            self.assertEqual((ai_gateway.gateway, ai_gateway.source), (env, 'env'))
            upstream.side_effect = None
            upstream.return_value = {'choices': [{'message': {'content': '{"room_type":"STANDARD","check_in":null,"check_out":null}'}}]}
            self.assertEqual(client.post('/api/v1/extract-booking', json={'raw_text': 'Standard', 'mode': 'openai'}).status_code, 200)
            self.assertEqual(upstream.call_args.args[0]['base_url'], env['base_url'])
            self.assertEqual(upstream.call_args.kwargs['payload']['model'], 'env-model')
            # Base URL để trống: chỉ đổi model của .env, URL sai còn trong vùng chờ không bị áp dụng
            self.assertEqual(client.post('/api/gateway/select', json={'model': 'env-model-2'}).status_code, 200)
            self.assertEqual(ai_gateway.gateway, {**env, 'model': 'env-model-2'})
            # URL chưa bấm "Kiểm tra" thì từ chối, không âm thầm bỏ qua
            self.assertEqual(client.post('/api/gateway/select', json={'model': 'x', 'base_url': 'https://khac.example/v1'}).status_code, 409)
            self.assertEqual(ai_gateway.gateway['base_url'], env['base_url'])
            # /models lỗi nhưng vẫn nhập model thủ công: form còn đúng URL vừa kiểm tra thì áp dụng gateway đó
            self.assertEqual(client.post('/api/gateway/select', json={'model': 'manual-id', 'base_url': typo['base_url']}).json(), {'model': 'manual-id'})
            self.assertEqual(ai_gateway.gateway, {**typo, 'model': 'manual-id'})
            self.assertEqual((ai_gateway.pending, ai_gateway.source), ({}, 'ui'))

    def test_public_ai_limit(self):
        async def local_app(scope, receive, send):
            scope['client'] = ('127.0.0.1', 1234)
            await app(scope, receive, send)
        local, tunnel = TestClient(local_app), TestClient(app, headers={'X-Forwarded-For': '203.0.113.5'})
        body = {'raw_text': 'Standard', 'mode': 'openai'}
        reply = {'choices': [{'message': {'content': '{"room_type":"STANDARD","check_in":null,"check_out":null}'}}]}
        with patch.dict(ai_gateway.gateway, {'base_url': 'https://gateway.example/v1', 'api_key': 'secret', 'model': 'm'}), \
                patch.object(ai_gateway, 'public_used', 0), \
                patch.object(ai_gateway, 'gateway_request', new_callable=AsyncMock, return_value=reply):
            with patch.object(booking, 'PUBLIC_AI_LIMIT', 0), patch.object(gateway_router, 'PUBLIC_AI_LIMIT', 0):
                self.assertEqual(tunnel.post('/api/v1/extract-booking', json=body).status_code, 403)
                self.assertIn("Number('0')", tunnel.get('/').text)
            with patch.object(booking, 'PUBLIC_AI_LIMIT', 2), patch.object(gateway_router, 'PUBLIC_AI_LIMIT', 2):
                self.assertIn("Number('2')", tunnel.get('/').text)
                self.assertEqual(local.post('/api/v1/extract-booking', json=body).status_code, 200)  # máy chủ không bị tính
                self.assertEqual([tunnel.post('/api/v1/extract-booking', json=body).status_code for _ in range(3)], [200, 200, 429])
                self.assertIn("Number('0')", tunnel.get('/').text)
                self.assertEqual(tunnel.post('/api/v1/extract-booking', json={**body, 'mode': 'regex'}).status_code, 200)
                self.assertEqual(tunnel.post('/api/gateway/select', json={'model': 'x'}).status_code, 403)  # cấu hình vẫn chỉ local


if __name__ == '__main__':
    unittest.main()
