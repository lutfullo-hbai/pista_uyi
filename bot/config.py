from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    channel_id: str = Field(alias="CHANNEL_ID")
    database_url: str = Field(alias="DATABASE_URL")
    web_app_url: str = Field(alias="WEB_APP_URL")
    admin_ids: list[int] = Field(default=[], alias="ADMIN_IDS")
    local_database_url: str | None = Field(default=None, alias="LOCAL_DATABASE_URL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def effective_database_url(self) -> str:
        if self.local_database_url:
            return self.local_database_url
        return self.database_url


settings = Settings()
