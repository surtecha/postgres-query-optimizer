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


def test_ollama_routes_locally_without_paid_credentials():
    from optimizer.providers import OllamaProvider

    provider = OllamaProvider(Settings(openai_api_key="", max_model_tokens=32000))
    provider.client.chat.completions.create = Mock(
        return_value=response_with_content(
            '{"candidates":[{"sql":"SELECT 1","hypothesis":"Check a constant"}]}'
        )
    )
    candidates, usage = provider.generate("SELECT 1", {}, 1)
    assert str(provider.client.base_url) == "http://localhost:11434/v1/"
    assert provider.client.api_key == "ollama"
    assert candidates[0].source == "ollama"
    assert usage["provider"] == "ollama"
    assert usage["model"] == "qwen2.5-coder:3b"
    assert usage["estimated_cost_usd"] == 0
    assert provider.client.chat.completions.create.call_args.kwargs["model"] == "qwen2.5-coder:3b"


def test_ollama_failure_keeps_deterministic_fallback_separate():
    import time
    from unittest.mock import MagicMock, patch

    from openai import APIConnectionError
    from optimizer.providers import OllamaProvider
    from optimizer.workflow import Workflow

    settings = Settings(openai_api_key="", max_model_tokens=32000)
    provider = OllamaProvider(settings)
    provider.client.chat.completions.create = Mock(
        side_effect=APIConnectionError(request=httpx.Request("POST", "http://localhost:11434"))
    )
    workflow = Workflow(MagicMock(), MagicMock(), settings, MagicMock())
    with patch("optimizer.workflow.OllamaProvider", return_value=provider):
        result = workflow.generation(
            {
                "request": {
                    "sql": "SELECT id FROM commerce.orders WHERE customer_id=731",
                    "provider": "ollama",
                },
                "metadata": {"indexes": []},
                "diagnostics": [],
                "started_at": time.time(),
            }
        )
    assert result["usage"]["error"] == "APIConnectionError"
    assert result["usage"]["provider"] == "ollama"
    assert result["candidates"]
    assert all(candidate["source"] == "deterministic" for candidate in result["candidates"])


def test_custom_openai_compatible_endpoint_and_model():
    provider = OpenAIProvider(
        Settings(
            openai_api_key="local-placeholder",
            openai_base_url="http://localhost:8080/v1",
            model="custom-code-model",
        )
    )
    assert str(provider.client.base_url) == "http://localhost:8080/v1/"
    assert provider.model == "custom-code-model"


def test_ollama_sends_bounded_schema_for_constrained_generation():
    from optimizer.providers import OllamaProvider

    provider = OllamaProvider(Settings(max_model_tokens=32000))
    provider.client.chat.completions.create = Mock(
        return_value=response_with_content('{"candidates":[]}')
    )
    candidates, usage = provider.generate("SELECT 1", {}, 1)
    assert candidates == []
    assert "error" not in usage
    payload = provider.client.chat.completions.create.call_args.kwargs
    format_ = payload["response_format"]
    assert format_["type"] == "json_schema"
    schema = format_["json_schema"]["schema"]
    assert schema["required"] == ["candidates"]
    assert schema["properties"]["candidates"]["maxItems"] == 1
    assert schema["additionalProperties"] is False
    assert "hypothesis" in schema["$defs"]["Candidate"]["required"]


def test_invalid_model_response_records_field_errors_without_input():
    from optimizer.providers import OllamaProvider

    provider = OllamaProvider(Settings(max_model_tokens=32000))
    provider.client.chat.completions.create = Mock(
        return_value=response_with_content('{"candidates":[{"sql":"SELECT secret_value"}]}')
    )
    candidates, usage = provider.generate("SELECT 1", {}, 1)
    assert candidates == []
    assert usage["error"] == "ValidationError"
    assert usage["validation_errors"][0]["loc"] == ("candidates", 0, "hypothesis")
    assert "secret_value" not in str(usage)
    assert usage["tokens"] == 123


def test_other_compatible_servers_keep_json_object_format():
    provider = provider_with_response(response_with_content('{"candidates":[]}'))
    provider.generate("SELECT 1", {}, 1)
    assert provider.client.chat.completions.create.call_args.kwargs["response_format"] == {
        "type": "json_object"
    }
