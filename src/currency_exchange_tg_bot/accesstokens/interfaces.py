import datetime
from typing import Protocol, Literal
from collections import namedtuple

tokenType = Literal['access', 'refresh']
AuthToken = namedtuple('AuthToken', ['data', 'expires_in'])


class SyncTokenRepositoryInterface(Protocol):

    def get_fresh_token(self, token_type: tokenType) -> AuthToken | None: ...

    def remove_expired_tokens(self, token_type: tokenType) -> int: ...

    def save_token(self, data: str, expiry_time: datetime.datetime, token_type: tokenType) -> None: ...

    def delete_all_tokens(self): ...
