from pydantic_settings import BaseSettings, SettingsConfigDict


class BraveSearchConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BRAVE_", env_file=".env", extra="ignore"
    )

    api_key: str
    base_url: str = "https://api.search.brave.com/res/v1"
    timeout: float = 5.0
