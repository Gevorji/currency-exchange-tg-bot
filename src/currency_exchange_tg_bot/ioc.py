from currency_exchange_fapi_client import Configuration, CurrencyExchangeApi, AuthApi

from currency_exchange_tg_bot import config
from currency_exchange_tg_bot.accesstokens import Sqlite3TokenRepository, get_sqlite3_connection, AccessTokenService
from currency_exchange_tg_bot.apitools import api_session_factory
from currency_exchange_tg_bot.botcallbacks import (StartCallback, GetAllCurrenciesCallback,
                                                   GetCurrencyConversationCallbacks, GetAllExchangeRatesCallback,
                                                   GetExchangeRateCallbacks, AddCurrencyConversationCallbacks,
                                                   AddExchangeRateConversationCallbacks,
                                                   UpdateExchangeRateConversationCallbacks,
                                                   ConvertCurrencyConversationCallbacks, ErrorHandler,
                                                   RevokeTokensCallback, ExpungeTokensCallback)
from currency_exchange_tg_bot.adminsrecord import AdminsRecord
from currency_exchange_tg_bot.accesstokens.db import create_schema

bot_settings = config.TgBotSettings(send_chat_ids_on_start=True)
api_settings = config.CurrencyExchangeApiSettings()
db_settings = config.Sqlite3Settings()

db_connection = get_sqlite3_connection(db_settings.connection_uri)
with db_connection() as conn:
    create_schema(conn)

token_repo = Sqlite3TokenRepository(db_connection)
auth_token_gateway = AccessTokenService(token_repo, api_settings)
configuration = Configuration(api_settings.host,
                              username=api_settings.username,
                              password=api_settings.password)
cur_exch_api_factory = api_session_factory(auth_token_gateway, configuration, CurrencyExchangeApi)
auth_api_factory = api_session_factory(auth_token_gateway, configuration, AuthApi, ensure_access_token_activeness=False)
admins_rec = AdminsRecord(bot_settings)

start_cb = StartCallback(cur_exch_api_factory, api_settings, send_chat_id=bot_settings.send_chat_ids_on_start)
allcurrencies_cb = GetAllCurrenciesCallback(cur_exch_api_factory, api_settings)
allexchange_rates_cb = GetAllExchangeRatesCallback(cur_exch_api_factory, api_settings)
get_currency_cbs = GetCurrencyConversationCallbacks(cur_exch_api_factory, api_settings)
get_exchange_rate_cbs = GetExchangeRateCallbacks(cur_exch_api_factory, api_settings)
add_currency_cbs = AddCurrencyConversationCallbacks(cur_exch_api_factory, api_settings)
add_exchange_rate_cbs = AddExchangeRateConversationCallbacks(cur_exch_api_factory, api_settings)
update_exchange_rate_cbs = UpdateExchangeRateConversationCallbacks(cur_exch_api_factory, api_settings)
convert_currency_cbs = ConvertCurrencyConversationCallbacks(cur_exch_api_factory, api_settings)
revoke_tokens_cb = RevokeTokensCallback(auth_token_gateway, admins_rec, auth_api_factory, api_settings)
expunge_tokens_cb = ExpungeTokensCallback(auth_token_gateway, admins_rec)
error_handler = ErrorHandler(admins_rec, bot_settings)