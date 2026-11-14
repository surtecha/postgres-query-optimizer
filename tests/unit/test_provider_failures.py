from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APITimeoutError
from optimizer.config import Settings
from optimizer.providers import OpenAIProvider


def provider_with_response(response):
    provider = OpenAIProvider(
        Settings(openai_api_key="test-not-a-real-key", max_model_tokens=32000)
    )
    provider.client.chat.completions.create = Mock(return_value=response)
    return provider


def response_with_content(content, reason="stop"):
    return SimpleNamespace(
        usage=SimpleNamespace(total_tokens=123),
        choices=[SimpleNamespace(finish_reason=reason, message=SimpleNamespace(content=content))],
    )


def test_empty_choices_falls_back_and_preserves_billed_usage():
    provider = provider_with_response(
        SimpleNamespace(choices=[], usage=SimpleNamespace(total_tokens=9))
    )
    candidates, usage = provider.generate("SELECT 1", {}, 1)
    assert candidates == []
    assert usage["error"] == "EmptyResponse"
    assert usage["calls"] == 1
    assert usage["tokens"] == 9


@pytest.mark.parametrize("content", [None, "", "   "])
def test_empty_content_is_reported(content):
    provider = provider_with_response(response_with_content(content))
    candidates, usage = provider.generate("SELECT 1", {}, 1)
    assert candidates == []
    assert usage["error"] == "EmptyResponse"
    assert usage["tokens"] == 123


def test_invalid_schema_retains_known_token_usage():
    provider = provider_with_response(response_with_content('{"candidates":[{"sql":"SELECT 1"}]}'))
    candidates, usage = provider.generate("SELECT 1", {}, 1)
    assert candidates == []
    assert usage["error"] == "ValidationError"
    assert usage["tokens"] == 123


def test_truncated_output_is_not_accepted_even_if_json_parses():
    provider = provider_with_response(response_with_content('{"candidates":[]}', "length"))
    candidates, usage = provider.generate("SELECT 1", {}, 1)
    assert candidates == []
    assert usage["error"] == "IncompleteResponse"


def test_timeout_has_unknown_usage_and_no_synthetic_candidate():
    provider = provider_with_response(None)
    provider.client.chat.completions.create.side_effect = APITimeoutError(
        request=httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    )
    candidates, usage = provider.generate("SELECT 1", {}, 1)
    assert candidates == []
    assert usage["error"] == "APITimeoutError"
    assert usage["tokens"] is None
    assert usage["calls"] == 1


def test_success_has_structured_candidates_and_known_usage():
    provider = provider_with_response(
        response_with_content(
            '{"candidates":[{"sql":"SELECT 1","hypothesis":"Check a constant expression"}]}'
        )
    )
    candidates, usage = provider.generate("SELECT 1", {}, 1)
    assert len(candidates) == 1
    assert candidates[0].source == "openai"
    assert usage["tokens"] == 123
    assert "error" not in usage
