import contextlib
import sqlite3
import datetime


sqlite3.register_adapter(datetime.datetime, lambda v: v.isoformat())
sqlite3.register_converter('datetime', lambda v: datetime.datetime.fromisoformat(v))


def get_sqlite3_connection(db_url: str):
    @contextlib.contextmanager
    def connect(*args, **kwargs):
        conn = sqlite3.connect(db_url, *args, **kwargs)
        try:
            yield conn
        except Exception:
            raise
        finally:
            conn.close()
    return connect

def create_schema(connection: sqlite3.Connection):
    with connection:
        connection.execute(
            '''CREATE TABLE IF NOT EXISTS token (
               data TEXT,
               token_type TEXT,
               expiry_date DATETIME
               );
            '''
        )