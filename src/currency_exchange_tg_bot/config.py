from pathlib import Path
from typing import Optional, Literal

from pydantic import HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Sqlite3Settings(BaseSettings):
    # a name of a file that is used by db to connect
    connection_uri: str = "accesstoken.sqlite3"


class TgBotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # token must be set in .env file
    tg_bot_token: str
    # change this if your file with admin chats ids is named differently
    admin_records_file: Path = 'admin_records'
    # on /start command, should the bot send chat id of this private chat with user
    send_chat_ids_on_start: bool = False
    # should the bot send a report whenever an error occurs trying to handle an update
    notify_admins_on_error: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class CurrencyExchangeApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', env_prefix='CURRENCY_EXCHANGE_')

    username: Optional[str] = None
    password: Optional[str] = None
    host: Optional[HttpUrl] = None

    # request timeout is set on each request to service api
    request_timeout: Optional[float] = 10.0

    @field_validator('host', mode='after')
    @classmethod
    def validate_host(cls, v):
        return v.scheme+'://' + v.host + ':' + str(v.port)
