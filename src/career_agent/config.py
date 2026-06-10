from pydantic_settings import BaseSettings, SettingsConfigDict


class CareerAgentConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CAREER_TAILOR_", env_file=".env", extra="ignore"
    )
    # Provider API keys are read by Pydantic AI at run time.
    model: str = "anthropic:claude-sonnet-4-6"
    request_limit: int = 100
