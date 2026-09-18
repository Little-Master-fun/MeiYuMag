import unittest
from unittest.mock import patch

import httpx

from app.core.config import settings
from app.services.ai_review import AiReviewService


class AiEndpointTests(unittest.IsolatedAsyncioTestCase):
    def test_document_times_use_china_timezone_and_auto_prompt_covers_yueyuan(self):
        service = AiReviewService()
        result = service.combine_datetime("2035-12-20", "09:00")
        self.assertEqual(result.utcoffset().total_seconds(), 8 * 3600)
        self.assertEqual(result.hour, 9)
        self.assertIn("连续自然日", service.build_prompt("auto"))
        self.assertIn("不得猜测", service.build_prompt("auto"))
        for kind in ('auto', 'meiyu_venue'):
            self.assertIn('借用时间可以是今天或过去', service.build_prompt(kind))
            self.assertIn('不要将过去日期改为未来日期', service.build_prompt(kind))
            self.assertIn('此补录规则不适用于悦园三楼', service.build_prompt(kind))

    async def test_root_and_versioned_bases_use_one_v1_prefix(self):
        client_class = httpx.AsyncClient
        for base in (
            "https://example.test",
            "https://example.test/",
            "https://example.test/v1",
            "https://example.test/v1/",
        ):
            with self.subTest(base=base):
                requests = []

                def respond(request):
                    requests.append(request)
                    return httpx.Response(200, json={"choices": []})

                transport = httpx.MockTransport(respond)
                with (
                    patch.object(settings, "ai_api_base_url", base),
                    patch.object(settings, "ai_api_key", "test-only-key"),
                    patch("app.services.ai_review.httpx.AsyncClient",
                          side_effect=lambda **kwargs: client_class(transport=transport, **kwargs)),
                ):
                    await AiReviewService().call_chat_completion("Test", "Synthetic text")
                self.assertEqual(len(requests), 1)
                self.assertEqual(str(requests[0].url), "https://example.test/v1/chat/completions")
                self.assertEqual(requests[0].headers["Authorization"], "Bearer test-only-key")
