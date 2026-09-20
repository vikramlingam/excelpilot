import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="inception/mercury-2.5", validation_alias="OPENROUTER_MODEL")
    openrouter_model_capable: str = Field(
        default="openai/gpt-5.6-luna", validation_alias="OPENROUTER_MODEL_CAPABLE"
    )
    openrouter_model_fallbacks: str = Field(
        default="qwen/qwen3.5-flash-02-23,openai/gpt-5.6-luna",
        validation_alias="OPENROUTER_MODEL_FALLBACKS",
    )
    llm_timeout_s: float = Field(default=90.0, validation_alias="LLM_TIMEOUT_S")
    openrouter_app_url: str = Field(
        default="https://github.com/vikramlingam/excelpilot", validation_alias="OPENROUTER_APP_URL"
    )
    openrouter_app_title: str = Field(default="ExcelPilot", validation_alias="OPENROUTER_APP_TITLE")
    openrouter_reasoning_effort: str = Field(
        default="low", validation_alias="OPENROUTER_REASONING_EFFORT"
    )

    typesafe_api_key: str = Field(default="", validation_alias="TYPESAFE_API_KEY")
    typesafe_base_url: str = Field(default="", validation_alias="TYPESAFE_BASE_URL")
    jev_model: str = Field(default="jev-latest", validation_alias="JEV_MODEL")
    jev_fallback_via_openrouter: bool = Field(
        default=True, validation_alias="JEV_FALLBACK_VIA_OPENROUTER"
    )
    jev_approve_threshold: float = Field(default=0.85, validation_alias="JEV_APPROVE_THRESHOLD")
    jev_block_threshold: float = Field(default=0.15, validation_alias="JEV_BLOCK_THRESHOLD")
    jev_verify_accept_confidence: float = Field(
        default=0.80, validation_alias="JEV_VERIFY_ACCEPT_CONFIDENCE"
    )
    jev_typesafe_timeout_s: float = Field(default=1.5, validation_alias="JEV_TYPESAFE_TIMEOUT_S")
    jev_openrouter_timeout_s: float = Field(default=4.0, validation_alias="JEV_OPENROUTER_TIMEOUT_S")

    excelpilot_host: str = Field(default="127.0.0.1", validation_alias="EXCELPILOT_HOST")
    excelpilot_port: int = Field(default=8765, validation_alias="EXCELPILOT_PORT")
    excelpilot_addin_origin: str = Field(
        default="https://localhost:3000", validation_alias="EXCELPILOT_ADDIN_ORIGIN"
    )
    excelpilot_data_dir: str = Field(default="~/.excelpilot", validation_alias="EXCELPILOT_DATA_DIR")
    excelpilot_redaction: str = Field(default="pii", validation_alias="EXCELPILOT_REDACTION")
    excelpilot_always_ask_before_writes: bool = Field(
        default=False, validation_alias="EXCELPILOT_ALWAYS_ASK_BEFORE_WRITES"
    )
    excelpilot_page_cells: int = Field(default=4000, validation_alias="EXCELPILOT_PAGE_CELLS")
    excelpilot_daily_budget_usd: float = Field(
        default=5.0, validation_alias="EXCELPILOT_DAILY_BUDGET_USD"
    )
    excelpilot_bridge_preference: str = Field(
        default="officejs,xlwings,file", validation_alias="EXCELPILOT_BRIDGE_PREFERENCE"
    )

    logfire_token: str = Field(default="", validation_alias="LOGFIRE_TOKEN")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @property
    def resolved_data_dir(self) -> Path:
        path = Path(os.path.expanduser(self.excelpilot_data_dir))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def fallback_models(self) -> list[str]:
        return [m.strip() for m in self.openrouter_model_fallbacks.split(",") if m.strip()]


settings = Settings()
