import datetime
from unittest.mock import MagicMock, AsyncMock
import sqlite3
import contextlib

import pytest
from currency_exchange_fapi_client import AuthApi

from currency_exchange_fapi_client.models import TokenCreatedResponse, AccessExpiresIn, RefreshExpiresIn

from currency_exchange_tg_bot.accesstokens import AccessTokenService, Sqlite3TokenRepository, AuthToken
from currency_exchange_tg_bot.accesstokens.db import create_schema
from currency_exchange_tg_bot.apitools import ApiClient


@pytest.fixture
def sqlite3_connection():
    conn = sqlite3.connect(":memory:")
    create_schema(conn)

    @contextlib.contextmanager
    def connection():
        yield conn

    yield connection
    conn.close()


@pytest.fixture(scope='module')
def db_config():
    class MockConfig:

        def __init__(self):
            self.host = 'host'
            self.username = 'user'
            self.password = 'password'
    return MockConfig()


@pytest.fixture(scope='module')
def mock_api_client():
    return MagicMock(ApiClient)


@pytest.fixture
def mock_auth_api():
    access_expires_in = datetime.datetime.now() + datetime.timedelta(minutes=1)
    refresh_expires_in = datetime.datetime.now() + datetime.timedelta(minutes=2)
    mock_token_response = TokenCreatedResponse(
        token_type='access',
        access_token='some_random_jwt',
        refresh_token='some_random_jwt',
        access_expires_in=AccessExpiresIn(int(access_expires_in.timestamp())),
        refresh_expires_in=RefreshExpiresIn(int(refresh_expires_in.timestamp())),
    )
    class MockApi:

        def __init__(self, *args, **kwargs): ...

        async def auth_create_token(self): ...

        async def auth_refresh_access_token(self): ...

    mock_api = MockApi
    mock_api.auth_create_token = AsyncMock(return_value=mock_token_response)
    mock_api.auth_refresh_access_token = AsyncMock(return_value=mock_token_response)

    return mock_api

@pytest.fixture
def patch_api_client(monkeypatch, mock_api_client):
    monkeypatch.setattr('currency_exchange_tg_bot.accesstokens.accesstokenservice.ApiClient', mock_api_client)

@pytest.fixture
def patch_auth_api(monkeypatch, mock_auth_api):
    monkeypatch.setattr('currency_exchange_tg_bot.accesstokens.accesstokenservice.AuthApi', mock_auth_api)


@pytest.fixture
def token_repo(sqlite3_connection) -> Sqlite3TokenRepository:
    return Sqlite3TokenRepository(sqlite3_connection)


@pytest.fixture
def access_token_service(db_config, token_repo) -> AccessTokenService:
    return AccessTokenService(token_repo, db_config)


pytestmark = [pytest.mark.usefixtures('patch_api_client', 'patch_auth_api'), pytest.mark.anyio]


async def test_get_access_token_from_db_success(access_token_service, token_repo):
    expired_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
    not_expired_time = datetime.datetime.now() + datetime.timedelta(minutes=1)
    token_repo.save_token('stale_token_data...', expired_time, 'access')
    token_repo.save_token('token_data...', not_expired_time, 'refresh')
    token_repo.save_token('fresh_token_data...', not_expired_time, 'access')

    token = await access_token_service.get_access_token()

    assert token == 'fresh_token_data...'


class TestGetAccessTokenThroughGainingFromApi:

    async def test_no_tokens_in_db(self, access_token_service, sqlite3_connection, mock_auth_api):
        token = await access_token_service.get_access_token()

        assert mock_auth_api.auth_create_token.called

        with sqlite3_connection() as conn:
            assert len(conn.execute('SELECT * FROM token').fetchall()) == 2

    async def test_expired_access_and_refresh_token_in_db(self, access_token_service, token_repo, sqlite3_connection, mock_auth_api):
        expired_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
        token_repo.save_token('token_data...', expired_time, 'access')
        token_repo.save_token('token_data...', expired_time, 'refresh')

        token = await access_token_service.get_access_token()

        assert mock_auth_api.auth_create_token.called
        with sqlite3_connection() as conn:
            assert len(conn.execute('SELECT * FROM token').fetchall()) == 2


class TestGetAccessTokenThroughRefreshing:

    async def test_one_fresh_and_one_expired_refresh_token_in_db(self, access_token_service, token_repo,
                                                                 sqlite3_connection, mock_auth_api):
        expired_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
        not_expired_time = datetime.datetime.now() + datetime.timedelta(minutes=1)
        token_repo.save_token('stale_token_data...', expired_time, 'refresh')
        token_repo.save_token('fresh_token_data...', not_expired_time, 'refresh')

        token = await access_token_service.get_access_token()

        mock_auth_api.auth_refresh_access_token.assert_called_with(grant_type='refresh_token',
                                                                   refresh_token='fresh_token_data...')
        with sqlite3_connection() as conn:
            assert len(conn.execute('SELECT * FROM token').fetchall()) == 2


    async def test_only_expired_refresh_tokens_in_db(self, access_token_service, token_repo, mock_auth_api):
        expired_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
        token_repo.save_token('token_data...', expired_time, 'refresh')

        await access_token_service.get_access_token()

        assert not mock_auth_api.auth_refresh_access_token.called


class TestTokenCashing:

    async def test_cached_token_returned(self, access_token_service, token_repo):
        token_repo.get_fresh_token = MagicMock(
            return_value=AuthToken('token_data', datetime.datetime.now()+datetime.timedelta(minutes=1)),
        )
        token = await access_token_service.get_access_token()
        another_token = await access_token_service.get_access_token()

        assert token is another_token
        token_repo.get_fresh_token.assert_called_once()

    async def test_expired_cached_token_not_returned(self, access_token_service, token_repo):
        cached_token = AuthToken('token_data', datetime.datetime.now() - datetime.timedelta(minutes=1))
        access_token_service._cached_access_token = cached_token
        token_repo.get_fresh_token = MagicMock(return_value=AuthToken('token_data', datetime.datetime.now()))
        token = await access_token_service.get_access_token()

        assert token is not cached_token
        assert token_repo.get_fresh_token.called
