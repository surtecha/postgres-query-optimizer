from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IndexProposal(Contract):
    table: str = Field(pattern=r"^[a-z_]+$")
    columns: list[str] = Field(min_length=1, max_length=3)
    include: list[str] = Field(default_factory=list, max_length=3)
    # Only structured equality predicates. Arbitrary DDL is never accepted.
    predicate_column: str | None = None
    predicate_value: str | int | None = None


class Candidate(Contract):
    sql: str = Field(min_length=1, max_length=20000)
    hypothesis: str = Field(min_length=1, max_length=2000)
    assumptions: list[str] = Field(default_factory=list, max_length=8)
    index: IndexProposal | None = None
    source: Literal["deterministic", "openai", "ollama"] = "deterministic"


class ModelResponse(Contract):
    candidates: list[Candidate] = Field(max_length=8)


class OptimizeRequest(Contract):
    sql: str = Field(min_length=1, max_length=20000)
    workload_id: str | None = Field(None, max_length=100)
    provider: Literal["deterministic", "openai", "ollama"] = "deterministic"


class Validation(Contract):
    status: Literal["statically_rejected", "differentially_validated", "failed", "inconclusive"]
    reason: str
    datasets: list[str] = Field(default_factory=list)
    structural_changes: dict[str, Any] = Field(default_factory=dict)


class ToolRequest(Contract):
    name: Literal["inspect", "explain", "equivalence", "benchmark"]
    sql: str = Field(max_length=20000)
