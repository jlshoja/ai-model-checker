import json
import time
import sys
from types import SimpleNamespace

import pytest

# ensure repo root is importable
sys.path.insert(0, "")

from check_models import (
    ProviderConfig,
    OpenAICompatibleProvider,
    AnthropicCompatibleProvider,
    ModelResult,
)


class DummyResp:
    def __init__(self, status_code=200, json_data=None, text="", iter_lines=None):
        self.status_code = status_code
        self._json = json_data
        self.text = text
        self._iter_lines = iter_lines

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def iter_lines(self, decode_unicode=True):
        if self._iter_lines is None:
            return iter(())
        return iter(self._iter_lines)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def make_session(monkeypatch, get_resp=None, post_resp=None):
    class S:
        def get(self, url, headers=None, timeout=None):
            return get_resp

        def post(self, url, headers=None, json=None, timeout=None, stream=False):
            return post_resp

        def mount(self, prefix, adapter):
            # no-op for tests
            return None

    return S()


def test_openai_fetch_and_plain_success(monkeypatch):
    cfg = ProviderConfig(name="p", type="openai", base_url="https://x", api_key="k")
    get_resp = DummyResp(status_code=200, json_data={"data": [{"id": "m1"}, {"id": "m2"}]})
    post_resp = DummyResp(status_code=200, json_data={"choices": [{"message": {"content": "OK"}}]})
    session = make_session(monkeypatch, get_resp, post_resp)
    monkeypatch.setattr('check_models.requests.Session', lambda: session)

    p = OpenAICompatibleProvider(cfg, timeout=5, test_prompt="hi", max_tokens=2)
    # override session created in constructor
    p.session = session
    models = p.fetch_models()
    assert models == ["m1", "m2"]
    r = p.test_model("m1")
    assert isinstance(r, ModelResult)
    assert r.status == "WORKING"


def test_openai_streaming_ttft(monkeypatch):
    cfg = ProviderConfig(name="p", type="openai", base_url="https://x", api_key="k", measure_ttft=True)
    # Simulate streaming lines
    lines = ["data: {\"choices\": [{\"delta\": {}}]}", "data: {\"choices\": [{\"delta\": {\"content\": \"h\"}}]}", "data: [DONE]"]
    post_resp = DummyResp(status_code=200, iter_lines=lines)
    session = make_session(monkeypatch, get_resp=None, post_resp=post_resp)
    monkeypatch.setattr('check_models.requests.Session', lambda: session)

    p = OpenAICompatibleProvider(cfg, timeout=5, test_prompt="hi", max_tokens=2)
    p.session = session
    r = p.test_model("m1")
    assert r.status == "WORKING"
    assert r.ttft_ms is not None


def test_anthropic_plain_failure(monkeypatch):
    cfg = ProviderConfig(name="a", type="anthropic", base_url="https://x", api_key="k")
    post_resp = DummyResp(status_code=400, json_data={"error": {"message": "bad"}}, text="bad")
    session = make_session(monkeypatch, get_resp=None, post_resp=post_resp)
    monkeypatch.setattr('check_models.requests.Session', lambda: session)

    p = AnthropicCompatibleProvider(cfg, timeout=5, test_prompt="hi", max_tokens=2)
    p.session = session
    r = p.test_model("m")
    assert r.status == "FAILED"
    assert "bad" in r.error


def test_plain_param_retry_on_400(monkeypatch):
    cfg = ProviderConfig(name="p", type="openai", base_url="https://x", api_key="k")
    # First POST returns 400 with unknown parameter error for max_tokens
    first_post_resp = DummyResp(status_code=400, json_data={"error": {"message": "unknown field 'max_tokens'"}}, text="unknown field 'max_tokens'")
    # Second POST (with alternate key) returns 200 with choices
    second_post_resp = DummyResp(status_code=200, json_data={"choices": [{"message": {"content": "OK"}}]})
    
    post_call_count = [0]
    
    class S:
        def get(self, url, headers=None, timeout=None):
            return DummyResp(status_code=200, json_data={"data": [{"id": "m1"}]})
        
        def post(self, url, headers=None, json=None, timeout=None, stream=False):
            post_call_count[0] += 1
            if post_call_count[0] == 1:
                return first_post_resp
            return second_post_resp
        
        def mount(self, prefix, adapter):
            return None
    
    session = S()
    monkeypatch.setattr('check_models.requests.Session', lambda: session)
    
    p = OpenAICompatibleProvider(cfg, timeout=5, test_prompt="hi", max_tokens=2)
    p.session = session
    r = p.test_model("m1")
    assert r.status == "WORKING"
    assert post_call_count[0] == 2


def test_plain_param_retry_fails(monkeypatch):
    cfg = ProviderConfig(name="p", type="openai", base_url="https://x", api_key="k")
    # First POST returns 400 with unknown parameter error
    first_post_resp = DummyResp(status_code=400, json_data={"error": {"message": "unknown field 'max_tokens'"}}, text="unknown field 'max_tokens'")
    # Second POST (with alternate key) also returns 400
    second_post_resp = DummyResp(status_code=400, json_data={"error": {"message": "unknown field 'max_completion_tokens'"}}, text="unknown field 'max_completion_tokens'")
    
    post_call_count = [0]
    
    class S:
        def get(self, url, headers=None, timeout=None):
            return DummyResp(status_code=200, json_data={"data": [{"id": "m1"}]})
        
        def post(self, url, headers=None, json=None, timeout=None, stream=False):
            post_call_count[0] += 1
            if post_call_count[0] == 1:
                return first_post_resp
            return second_post_resp
        
        def mount(self, prefix, adapter):
            return None
    
    session = S()
    monkeypatch.setattr('check_models.requests.Session', lambda: session)
    
    p = OpenAICompatibleProvider(cfg, timeout=5, test_prompt="hi", max_tokens=2)
    p.session = session
    r = p.test_model("m1")
    assert r.status == "FAILED"
    assert "retry" in r.error.lower()
    assert post_call_count[0] == 2
