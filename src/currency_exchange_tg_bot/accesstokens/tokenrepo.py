import sqlite3
import datetime
from typing import Callable

from .interfaces import SyncTokenRepositoryInterface, tokenType, AuthToken



class Sqlite3TokenRepository(SyncTokenRepositoryInterface):

    def __init__(self, connection: Callable[..., sqlite3.Connection]):
        self._db_connection = connection

    def get_fresh_token(self, token_type: tokenType) -> AuthToken | None:
        with self._db_connection() as conn:
            res = conn.execute("SELECT * FROM token WHERE token_type = ? "
                               "AND strftime('%Y-%m-%d %H:%M:%S', expiry_date) > datetime('now', 'localtime') LIMIT 1;",
                               (token_type,)).fetchone()
            if res is not None:
                return AuthToken(res[0], res[1])
            else:
                return res

    def remove_expired_tokens(self, token_type: tokenType) -> int:
        with self._db_connection() as conn:
            with conn:
                res = conn.execute("DELETE FROM token WHERE token_type = ? "
                                   "AND strftime('%Y-%m-%d %H:%M:%S', expiry_date) < datetime('now', 'localtime') "
                                   "RETURNING *;", (token_type,))
                return res.rowcount

    def save_token(self, data: str, expiry_time: datetime.datetime, token_type: tokenType) -> None:
        with self._db_connection() as conn:
            with conn:
                conn.execute('INSERT INTO token VALUES (?, ?, ?);', (data, token_type, expiry_time))

    def delete_all_tokens(self):
        with self._db_connection() as conn:
            with conn:
                conn.execute('DELETE FROM token;')
