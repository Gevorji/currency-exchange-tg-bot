import datetime
from typing import Callable
import logging


from currency_exchange_fapi_client import Configuration, TokenCreatedResponse
from currency_exchange_fapi_client.api_client import ApiClient
from currency_exchange_fapi_client.api import AuthApi

from .interfaces import SyncTokenRepositoryInterface, AuthToken, tokenType


logger = logging.getLogger('auth_token_service')


class AccessTokenService:

    def __init__(self, token_repo: SyncTokenRepositoryInterface, settings):
        self._api_settings = settings
        self._token_repo = token_repo
        self._configuration = Configuration(
            host = settings.host,
            username = settings.username,
            password = settings.password
        )
        self._cached_access_token: AuthToken | None = None

    async def get_access_token(self, *, invalidate_cache=False) -> str:
        if invalidate_cache:
            self.invalidate_cached_access_token()

        if self._cached_access_token_is_fresh():
            logger.debug('Returning cached access token')
            return self._cached_access_token.data

        token = self._token_repo.get_fresh_token(token_type='access')
        if token:
            logger.debug('Returning fresh token from db')
        if token is None:
            logger.debug('Refreshing token')
            token = await self._refresh_access_token()
            if token:
                logger.debug('Returning fresh token obtained through refresh')
        if token is None:
            logger.debug('Gaining token')
            token = await self._gain_token()
            logger.debug('Returning newly gained token')

        self._cached_access_token = token
        logger.debug('Token was cached')
        return token.data

    def invalidate_cached_access_token(self):
        logger.debug('Invalidating cached access token')
        self._cached_access_token = None

    def _cached_access_token_is_fresh(self) -> bool:
        if self._cached_access_token is not None and self._cached_access_token.expires_in > datetime.datetime.now():
            return True
        else:
            return False

    async def _gain_token(self) -> AuthToken:
        async with ApiClient(self._configuration) as api_client:
            auth = AuthApi(api_client)
            settings = self._api_settings
            response = await auth.auth_create_token(settings.username, settings.password)
            self.remove_all_tokens()
            auth_tokens = self._response_as_auth_tokens(response)
            self._save_token(auth_tokens['access'], 'access')
            self._save_token(auth_tokens['refresh'], 'refresh')
            return auth_tokens['access']

    async def _refresh_access_token(self) -> AuthToken | None:
        async with ApiClient(self._configuration) as api_client:
            refresh_token = self._token_repo.get_fresh_token(token_type='refresh')
            auth = AuthApi(api_client)
            if refresh_token is not None:
                response = await auth.auth_refresh_access_token(grant_type='refresh_token',
                                                                refresh_token=refresh_token.data)
                self.remove_all_tokens()
                auth_tokens = self._response_as_auth_tokens(response)
                self._save_token(auth_tokens['access'], 'access')
                self._save_token(auth_tokens['refresh'], 'refresh')
                return auth_tokens['access']
            else:
                return None

    def remove_all_tokens(self):
        self._token_repo.delete_all_tokens()

    def _save_token(self, token: AuthToken, type_: tokenType):

        self._token_repo.save_token(
            token.data, token.expires_in, type_)

    def _response_as_auth_tokens(self, response: TokenCreatedResponse) -> dict[str, AuthToken]:
        access_token, refresh_token = response.access_token, response.refresh_token
        access_expires_in = datetime.datetime.fromtimestamp(response.access_expires_in.actual_instance)
        refresh_expires_in = datetime.datetime.fromtimestamp(response.refresh_expires_in.actual_instance)
        return {
            'access': AuthToken(access_token, access_expires_in),
            'refresh': AuthToken(refresh_token, refresh_expires_in),
        }
