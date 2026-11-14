import pytest
from optimizer.config import Settings
from optimizer.models import ModelResponse
from optimizer.providers import DeterministicProvider, OpenAIProvider
from optimizer.safety import normalize


def test_deterministic_candidate_contract():
    candidates, usage = DeterministicProvider().generate(
        "SELECT id FROM commerce.orders WHERE customer_id=731", {"metadata": {"indexes": []}}, 8
    )
    assert candidates
    assert candidates[0].index.columns == ["customer_id"]
    assert usage["tokens"] == 0
    ModelResponse(candidates=candidates)


def test_malformed_model_output_rejected():
    with pytest.raises(ValueError):
        ModelResponse.model_validate_json(
            '{"candidates":[{"sql":"SELECT 1","execute":"DROP TABLE x"}]}'
        )


def test_model_context_budget_avoids_call():
    settings = Settings(openai_api_key="test-not-a-real-key", max_model_tokens=256)
    results, usage = OpenAIProvider(settings).generate("SELECT 1", {"diagnostics": ["x" * 1000]}, 8)
    assert results == []
    assert usage["calls"] == 0


def test_normalization_deduplication():
    assert normalize("select id from commerce.orders") == normalize(
        "SELECT id FROM commerce.orders"
    )
