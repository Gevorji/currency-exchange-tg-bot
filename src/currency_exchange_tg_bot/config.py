from pathlib import Path
from typing import Optional

from pydantic import HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Sqlite3Settings(BaseSettings):
    connection_uri: str = "accesstoken.sqlite3"


class TgBotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    tg_bot_token: str
    admin_records_file: Path = 'admin_records'
    send_chat_ids_on_start: bool = False
    notify_admins_on_error: bool = True


class CurrencyExchangeApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', env_prefix='CURRENCY_EXCHANGE_')

    username: Optional[str] = None
    password: Optional[str] = None
    host: Optional[HttpUrl] = None
    request_timeout: Optional[float] = 10.0

    @field_validator('host', mode='after')
    @classmethod
    def validate_host(cls, v):
        return v.scheme+'://' + v.host + ':' + str(v.port)
