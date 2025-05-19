from functools import partial
from typing import Protocol, Callable, Union, Optional
from copy import copy

from currency_exchange_fapi_client.api import CurrencyExchangeApi, AuthApi, UsersApi
from currency_exchange_fapi_client.api_client import ApiClient
from currency_exchange_fapi_client.configuration import Configuration


ApiType = type[Union[CurrencyExchangeApi, AuthApi, UsersApi]]


class AccessTokenGatewayProtocol(Protocol):

    async def get_access_token(self): ...


class ApiSession:

    def __init__(self, api_type: ApiType, access_token_gateway: AccessTokenGatewayProtocol,
                 configuration: Configuration, *, ensure_access_token_is_active: bool = True):
        self._configuration = copy(configuration)
        self._api_type = api_type
        self._access_token_gateway = access_token_gateway
        self._ensure_access_token_is_active = ensure_access_token_is_active

    async def __aenter__(self):
        self._api_client = ApiClient(self._configuration)
        if self._ensure_access_token_is_active:
            await self._ensure_active_access_token()
        return self._api_type(self._api_client)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._api_client.close()

    async def _ensure_active_access_token(self):
        active_token = await self._access_token_gateway.get_access_token()
        self._configuration.access_token = active_token


def api_session_factory(access_token_gateway: AccessTokenGatewayProtocol,
                        configuration: Configuration, api_type: Optional[ApiType] = None, *,
                        ensure_access_token_activeness: bool = True) -> Callable[..., ApiSession]:
    if api_type:
        def _make_session():
            return ApiSession(api_type, access_token_gateway, configuration,
                              ensure_access_token_is_active=ensure_access_token_activeness)
    else:
        def _make_session(api_type: ApiType):
            return ApiSession(api_type, access_token_gateway, configuration,
                              ensure_access_token_is_active=ensure_access_token_activeness)

    return _make_session
