import asyncio
import json
import unittest
from contextlib import ExitStack
from io import BytesIO
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import UploadFile

from app.core.config import Settings, settings
from app.services.ai_review import AiReviewService


MODELS = ['Ali-dashscope/MiniMax-M2.5', 'Ali-dashscope/Qwen3-Max', 'Ali-dashscope/Kimi-K2.5']


def response(passed=True):
    return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({
        'passed': passed, 'venue_name': '会议室',
        'issues': [] if passed else [{'type': 'MISSING_TIME', 'message': '请填写使用时间'}],
    })}}]})


class AiFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def run_review(self, handler, timeout=1, fallback=None):
        requests = []
        async def respond(request):
            payload = json.loads(request.content)
            requests.append(payload)
            return await handler(request, payload)
        client_class = httpx.AsyncClient
        with ExitStack() as stack:
            for key, value in {
                'ai_api_base_url': 'https://example.test/v1',
                'ai_api_key': 'secret-must-not-be-logged', 'ai_model': MODELS[0],
                'ai_fallback_models': ','.join(MODELS[1:]) if fallback is None else fallback,
                'ai_timeout_seconds': timeout,
            }.items():
                stack.enter_context(patch.object(settings, key, value))
            stack.enter_context(patch('app.services.ai_review.word_parser_service.extract_text',
                new=AsyncMock(return_value='private-document-must-not-be-logged')))
            stack.enter_context(patch('app.services.ai_review.httpx.AsyncClient',
                side_effect=lambda **kwargs: client_class(transport=httpx.MockTransport(respond), **kwargs)))
            result = await AiReviewService().pre_review_word('auto', UploadFile(filename='test.docx',file=BytesIO()))
        return result, requests

    def test_defaults_deduplicate_and_can_disable_fallbacks(self):
        self.assertEqual(Settings(_env_file=None).ai_review_models, MODELS)
        self.assertEqual(Settings(_env_file=None, ai_fallback_models='').ai_review_models, MODELS[:1])
        self.assertEqual(Settings(_env_file=None, ai_fallback_models=f' {MODELS[0]}, {MODELS[1]},,{MODELS[1]}').ai_review_models, MODELS[:2])

    async def test_first_success_or_business_rejection_never_calls_fallback(self):
        for passed in (True, False):
            async def handler(request, payload):
                return response(passed)
            result, requests = await self.run_review(handler)
            self.assertEqual(result.passed, passed)
            self.assertEqual([r['model'] for r in requests], MODELS[:1])

    async def test_request_errors_advance_in_exact_order_and_stop_on_success(self):
        async def handler(request, payload):
            if payload['model'] == MODELS[0]:
                raise httpx.ConnectError('network test', request=request)
            if payload['model'] == MODELS[1]:
                return httpx.Response(503)
            return response()
        result, requests = await self.run_review(handler)
        self.assertTrue(result.passed)
        self.assertEqual([r['model'] for r in requests], MODELS)

    async def test_bad_json_uses_second_model(self):
        async def handler(request, payload):
            if payload['model'] == MODELS[0]:
                return httpx.Response(200, json={'choices':[{'message':{'content':'not JSON'}}]})
            return response()
        result, requests = await self.run_review(handler)
        self.assertTrue(result.passed)
        self.assertEqual([r['model'] for r in requests], MODELS[:2])

    async def test_wall_clock_timeout_reaches_next_model(self):
        async def handler(request, payload):
            if payload['model'] == MODELS[0]:
                await asyncio.sleep(0.1)
            return response()
        result, requests = await self.run_review(handler, timeout=0.02)
        self.assertTrue(result.passed)
        self.assertEqual([r['model'] for r in requests], MODELS[:2])

    async def test_compatibility_retry_stays_on_same_model(self):
        async def handler(request, payload):
            return httpx.Response(400) if 'response_format' in payload else response()
        result, requests = await self.run_review(handler)
        self.assertTrue(result.passed)
        self.assertEqual([r['model'] for r in requests], [MODELS[0]] * 2)
        self.assertNotIn('response_format', requests[1])

    async def test_all_fail_returns_manual_review_marker_without_sensitive_logs(self):
        async def handler(request, payload):
            return httpx.Response(429, text='private-document-must-not-be-logged secret-must-not-be-logged')
        with self.assertLogs('app.services.ai_review', level='WARNING') as logs:
            result, requests = await self.run_review(handler)
        self.assertFalse(result.passed)
        self.assertEqual(result.issues[0].type, 'AI_REVIEW_REQUEST_FAILED')
        self.assertEqual([r['model'] for r in requests], MODELS)
        self.assertNotIn('must-not-be-logged', '\n'.join(logs.output))

    async def test_disabled_fallback_sends_only_primary_request(self):
        async def handler(request, payload):
            return httpx.Response(500)
        result, requests = await self.run_review(handler, fallback='')
        self.assertFalse(result.passed)
        self.assertEqual([r['model'] for r in requests], MODELS[:1])
