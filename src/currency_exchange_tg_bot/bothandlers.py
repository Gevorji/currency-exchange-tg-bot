from telegram.ext import CommandHandler, ConversationHandler, MessageHandler
from telegram.ext import filters

from currency_exchange_tg_bot.ioc import (allcurrencies_cb, allexchange_rates_cb, start_cb, get_currency_cbs,
                                          get_exchange_rate_cbs, add_currency_cbs, add_exchange_rate_cbs,
                                          update_exchange_rate_cbs, convert_currency_cbs, revoke_tokens_cb,
                                          expunge_tokens_cb)


handlers = [
    CommandHandler('start', start_cb),
    CommandHandler('allcurrencies', allcurrencies_cb),
    CommandHandler('allexchangerates', allexchange_rates_cb),
    ConversationHandler(
        entry_points=[CommandHandler('showcurrency', get_currency_cbs.start)],
        states={get_currency_cbs.ENTER_CODE: [MessageHandler(filters.TEXT, get_currency_cbs.send_currency)]},
        fallbacks=[MessageHandler(~filters.TEXT, get_currency_cbs.received_not_text)]
    ),
    ConversationHandler(
        entry_points=[CommandHandler('showexchangerate', get_exchange_rate_cbs.start)],
        states={
            get_exchange_rate_cbs.ENTER_CODES: [MessageHandler(filters.TEXT, get_exchange_rate_cbs.send_exchange_rate)]
        },
        fallbacks=[MessageHandler(~filters.TEXT, get_exchange_rate_cbs.received_not_text)]
    ),
    ConversationHandler(
        entry_points=[CommandHandler('addcurrency', add_currency_cbs.start)],
        states={
            add_currency_cbs.ENTER_FIELDS: [MessageHandler(filters.TEXT, add_currency_cbs.add_currency)]
        },
        fallbacks=[MessageHandler(~filters.TEXT, add_currency_cbs.received_not_text)]
    ),
    ConversationHandler(
        entry_points=[CommandHandler('addexchangerate', add_exchange_rate_cbs.start)],
        states={
            add_exchange_rate_cbs.ENTER_FIELDS: [MessageHandler(filters.TEXT, add_exchange_rate_cbs.add_exchange_rate)]
        },
        fallbacks=[MessageHandler(~filters.TEXT, add_exchange_rate_cbs.received_not_text)]
    ),
    ConversationHandler(
        entry_points=[CommandHandler('editexchangerate', update_exchange_rate_cbs.start)],
        states={
            update_exchange_rate_cbs.ENTER_FIELDS: [MessageHandler(filters.TEXT,
                                                                update_exchange_rate_cbs.update_exchange_rate)]
        },
        fallbacks=[MessageHandler(~filters.TEXT, update_exchange_rate_cbs.received_not_text)]
    ),
    ConversationHandler(
        entry_points=[CommandHandler('convertcurrency', convert_currency_cbs.start)],
        states={
            convert_currency_cbs.ENTER_BASE: [MessageHandler(filters.TEXT,
                                                                convert_currency_cbs.receive_currency)],
            convert_currency_cbs.ENTER_TARGET: [MessageHandler(filters.TEXT,
                                                                convert_currency_cbs.receive_currency)],
            convert_currency_cbs.ENTER_AMOUNT: [MessageHandler(filters.TEXT,
                                                                convert_currency_cbs.receive_amount)],
        },
        fallbacks=[MessageHandler(~filters.TEXT, convert_currency_cbs.received_not_text)]
    ),
    CommandHandler('revoketokens', revoke_tokens_cb),
    CommandHandler('expungetokens', expunge_tokens_cb),
]
