from __future__ import annotations

from types import SimpleNamespace

import pytest

import raise_assistant.providers.openai_provider as openai_module
from raise_assistant.providers.openai_provider import MAX_RESPONSE_PARTS, OpenAIProvider


class FakeResponses:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def response(response_id: str, text: str, *, incomplete: bool = False):
    return SimpleNamespace(
        id=response_id,
        output_text=text,
        status="incomplete" if incomplete else "completed",
        incomplete_details=SimpleNamespace(reason="max_output_tokens") if incomplete else None,
    )


def provider_with(monkeypatch, responses):
    fake_responses = FakeResponses(responses)
    monkeypatch.setattr(
        openai_module,
        "OpenAI",
        lambda api_key: SimpleNamespace(responses=fake_responses),
    )
    return OpenAIProvider("test-key", "test-model", 100), fake_responses


def test_openai_provider_continues_incomplete_output(monkeypatch):
    provider, fake = provider_with(
        monkeypatch,
        [
            response("first", "# Document\n\n## 1. First", incomplete=True),
            response("second", "\n\n## 2. Second"),
        ],
    )

    result = provider.generate("system rules", "write the document")

    assert result == "# Document\n\n## 1. First\n\n## 2. Second"
    assert len(fake.calls) == 2
    assert fake.calls[1]["previous_response_id"] == "first"
    assert fake.calls[1]["instructions"] == "system rules"


def test_openai_provider_never_returns_partial_output_after_retry_limit(monkeypatch):
    provider, _fake = provider_with(
        monkeypatch,
        [response(str(index), f"part {index}", incomplete=True) for index in range(MAX_RESPONSE_PARTS)],
    )

    with pytest.raises(RuntimeError, match="No partial output was saved"):
        provider.generate("system rules", "write the document")
