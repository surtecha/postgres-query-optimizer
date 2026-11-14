from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PGO_", env_file=".env", extra="ignore")
    app_dsn: SecretStr = SecretStr(
        "postgresql+psycopg://pgo_app:local_app_only@localhost:5433/pgo_app"
    )
    read_dsn: SecretStr = SecretStr(
        "postgresql://pgo_reader:local_reader_only@localhost:5434/pgo_benchmark"
    )
    admin_dsn: SecretStr = SecretStr(
        "postgresql://pgo_experiment:local_experiment_only@localhost:5434/pgo_benchmark"
    )
    state_dir: Path = Path("state")
    provider: Literal["deterministic", "openai", "ollama"] = "deterministic"
    model: str = "gpt-4.1-mini"
    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5-coder:3b"
    model_timeout_seconds: int = Field(default=90, ge=1, le=120)
    api_token: SecretStr = SecretStr("")
    deployment: Literal["local", "remote"] = "local"
    max_candidates: int = Field(default=8, ge=1, le=8)
    max_rounds: int = Field(default=3, ge=1, le=3)
    statement_ms: int = Field(default=30_000, ge=100, le=30_000)
    session_seconds: int = Field(default=300, ge=5, le=300)
    repetitions: int = Field(default=10, ge=5, le=50)
    min_improvement: float = Field(default=0.10, ge=0, le=0.9)
    max_cv: float = Field(default=0.35, gt=0, le=2)
    max_index_bytes: int = Field(default=67_108_864, ge=0)
    max_model_tokens: int = Field(default=6000, ge=256, le=32000)
    max_pending: int = Field(default=16, ge=1, le=100)
    max_result_rows: int = Field(default=50_000, ge=1, le=100_000)
    max_result_bytes: int = Field(default=16_777_216, ge=1024, le=67_108_864)
    max_plan_cost: float = Field(default=10_000_000, gt=0)
    otlp_endpoint: str = ""

    @model_validator(mode="after")
    def remote_auth(self) -> "Settings":
        if self.deployment == "remote" and len(self.api_token.get_secret_value()) < 32:
            raise ValueError("Remote deployment requires an API token of at least 32 characters")
        return self
