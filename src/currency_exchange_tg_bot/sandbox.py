import asyncio
from pprint import pprint
import os
from pathlib import Path

import currency_exchange_fapi_client
from currency_exchange_fapi_client.models.currency_out_schema import CurrencyOutSchema
from currency_exchange_fapi_client.rest import ApiException
from currency_exchange_tg_bot.config import CurrencyExchangeApiSettings


os.chdir(Path.cwd().resolve().parent.parent)

api_settings = CurrencyExchangeApiSettings()

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = currency_exchange_fapi_client.Configuration(
    host = str(api_settings.host), username=api_settings.username, password=api_settings.password
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

async def gain_token(conf):
    async with currency_exchange_fapi_client.ApiClient(configuration) as api_client:
        # Create an instance of the API class
        api_instance = currency_exchange_fapi_client.AuthApi(api_client)

        try:
            # Get All Currencies
            api_response = await api_instance.auth_create_token(username=api_settings.username,
                                                                password=api_settings.password)
            pprint(api_response)
            return api_response
        except Exception as e:
            print("Exception when calling CurrencyExchangeApi->currency_exchange_get_all_currencies: %s\n" % e)

async def get_all_currencies(conf):
    async with currency_exchange_fapi_client.ApiClient(configuration) as api_client:
        # Create an instance of the API class
        api_instance = currency_exchange_fapi_client.CurrencyExchangeApi(api_client)

        try:
            # Get All Currencies
            api_response = await api_instance.currency_exchange_get_all_currencies()
            print("The response of CurrencyExchangeApi->currency_exchange_get_all_currencies:\n")
            pprint(api_response)
            return api_response
        except Exception as e:
            print(f'type of exc: {type(e)}')
            print("Exception when calling CurrencyExchangeApi->currency_exchange_get_all_currencies: %s\n" % e)

async def main():
    token_response = await gain_token(configuration)
    configuration.access_token = token_response.access_token[::-1]

    all_currencies = await get_all_currencies(configuration)


if __name__ == '__main__':
    asyncio.run(main())
