import json
import os
import unittest
from unittest.mock import patch

from svea_eval.backends import GenerationConfig, OpenAICompatibleBackend
from svea_eval.data import load_suite


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(
            {
                "id": "chatcmpl-test",
                "created": 1,
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "A"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 1},
            }
        ).encode()


class BackendTests(unittest.TestCase):
    def test_openai_compatible_backend_uses_chat_contract(self):
        old_key = os.environ.get("SVEA_TEST_KEY")
        os.environ["SVEA_TEST_KEY"] = "secret-for-local-test"
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return _FakeResponse()

        try:
            _, items = load_suite()
            backend = OpenAICompatibleBackend(
                model_id="test-model",
                base_url="http://127.0.0.1:8000/v1",
                api_key_env="SVEA_TEST_KEY",
            )
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                generation = backend.generate(item=items[0], config=GenerationConfig())
        finally:
            if old_key is None:
                os.environ.pop("SVEA_TEST_KEY", None)
            else:
                os.environ["SVEA_TEST_KEY"] = old_key

        request = captured["request"]
        payload = json.loads(request.data)
        self.assertEqual(generation.text, "A")
        self.assertEqual(generation.input_tokens, 20)
        self.assertEqual(generation.output_tokens, 1)
        self.assertEqual(request.full_url, "http://127.0.0.1:8000/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-for-local-test")
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["seed"], 17)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(captured["timeout"], 120.0)
