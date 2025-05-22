import json
import re
import traceback
from typing import AsyncContextManager, Callable
import html
import logging

from tabulate import tabulate
import telegram
import telegram.ext
from telegram import Update
from telegram.ext import ContextTypes

from currency_exchange_fapi_client import exceptions as apiexc

from currency_exchange_tg_bot.adminsrecord import AdminsRecord
from currency_exchange_tg_bot.config import TgBotSettings, CurrencyExchangeApiSettings
from currency_exchange_tg_bot.accesstokens import AccessTokenService


logger = logging.getLogger('tg_bot')


WELCOMING_MSG = ('Привет! При помощи бота обмена валюты ты можешь:\n'
                 '- запросить имеющиеся валюты и обменные курсы;\n'
                 '- добавить новую валюту/обменный курс или изменить уже существующие;\n'
                 '- перевести одну валюту в другую\n'
                 'Имей в виду, что боту могут быть известны не все валюты или обменные курсы между ними, так'
                 ' что не расстраивайся, если не получил то, чего хотел\U0001F609\n')

RESPONSE_TABLEFMT = 'psql'

CURRENCY_CODE_PATTERN = re.compile('^ *[a-zA-Z]{3} *$')

CURRENCY_AMOUNT_PATTERN = re.compile('-?\\d+(\\.\\d+)?')


def make_currencies_table(data: list[tuple[str, str, str]]):
    return tabulate(data, ('Code', 'Name', 'Sign'), tablefmt=RESPONSE_TABLEFMT)


def make_exchange_rates_table(data: list[tuple[str, str, float]]):
    return tabulate(data, tablefmt=RESPONSE_TABLEFMT)


class BaseCallback:

    def __init__(self, api_session_factory: Callable[..., AsyncContextManager],
                 api_settings: CurrencyExchangeApiSettings):
        self.api_session = api_session_factory
        self.api_settings = api_settings


class BaseConverastionCallbacks:
    END = -1
    TIMEOUT = -2


class BaseTextConversationCallbacks(BaseConverastionCallbacks):

    async def received_not_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Я ожидаю получить только текст\U0001F62C')
        return self.END


class StartCallback(BaseCallback):

    def __init__(self, *args, send_chat_id: bool = False, **kwargs):
        self._send_chat_id = send_chat_id
        super().__init__(*args, **kwargs)

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id_msg = f'chat_id: {update.message.chat_id}\n' if self._send_chat_id else ''
        await context.bot.send_message(chat_id=update.effective_chat.id, text=WELCOMING_MSG+chat_id_msg)


class GetAllCurrenciesCallback(BaseCallback):

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        async with self.api_session() as api:
            response = await api.currency_exchange_get_all_currencies(_request_timeout=self.api_settings.request_timeout)
            msg = html.escape(make_currencies_table([(crncy.code, crncy.name, crncy.sign) for crncy in response]))
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'<pre>{msg}</pre>',
            parse_mode=telegram.constants.ParseMode.HTML
        )


class GetAllExchangeRatesCallback(BaseCallback):

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        async with self.api_session() as api:
            response = await api.currency_exchange_get_all_exchange_rates(
                _request_timeout=self.api_settings.request_timeout
            )
        msg = html.escape(
            make_currencies_table([(er.base_currency.code, er.target_currency.code, er.rate) for er in response])
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'<pre>{msg}</pre>',
            parse_mode=telegram.constants.ParseMode.HTML
        )


class GetCurrencyConversationCallbacks(BaseCallback, BaseTextConversationCallbacks):

    ENTER_CODE = 1

    _input_pattern = CURRENCY_CODE_PATTERN

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Отправь код валюты (три латинские буквы)')

        return self.ENTER_CODE

    async def send_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        code = update.message.text
        if not self._is_valid_code_input(code):
            await bot.send_message(chat_id=update.effective_chat.id, text='Какой-то неправильный код валюты\U0001F615')
            return self.END

        try:
            async with self.api_session() as api:
                currency = await api.currency_exchange_get_currency(code,
                                                                    _request_timeout=self.api_settings.request_timeout)
        except apiexc.NotFoundException:
            await bot.send_message(chat_id=update.effective_chat.id,
                                   text='Такую валюту найти не получилось\U0001F937')
            return self.END

        msg = make_currencies_table([(currency.code, currency.name, currency.sign)])

        await bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'<pre>{msg}</pre>',
            parse_mode=telegram.constants.ParseMode.HTML
        )

        return self.END

    def _is_valid_code_input(self, code: str):
        return bool(re.fullmatch(self._input_pattern, code))


class GetExchangeRateCallbacks(BaseCallback, BaseTextConversationCallbacks):

    ENTER_CODES = 1

    _input_pattern = re.compile('[a-zA-Z]{3} [a-zA-Z]{3}')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Отправь коды валюты (по три латинских буквы разделенных пробелом, '
                                            'например USD EUR)')

        return self.ENTER_CODES

    async def send_exchange_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        codes = update.message.text
        if not self._is_valid_codes_input(codes):
            await bot.send_message(chat_id=update.effective_chat.id, text='Неправильные коды валют\U0001F937')
            return self.END

        try:
            async with self.api_session() as api:
                er = await api.currency_exchange_get_exchange_rate(''.join(codes.upper().split(' ')),
                                                                   _request_timeout=self.api_settings.request_timeout)
        except apiexc.NotFoundException:
            await bot.send_message(chat_id=update.effective_chat.id,
                                   text='Такой курс найти не получилось\U0001F937')
            return self.END

        msg = html.escape(make_exchange_rates_table([(er.base_currency.code, er.target_currency.code, er.rate)]))

        await bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Держи\n<pre>{msg}</pre>',
            parse_mode=telegram.constants.ParseMode.HTML
        )

        return self.END

    def _is_valid_codes_input(self, codes: str):
        return bool(re.fullmatch(self._input_pattern, codes))


class AddCurrencyConversationCallbacks(BaseCallback, BaseTextConversationCallbacks):

    ENTER_FIELDS = 1

    _input_pattern = re.compile('^ *([a-zA-z]{3}). +([a-zA-Z ]+), +([^\\s_]+) *$')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Отправь код, имя и символ валюты в формате <код, имя, символ> (без скобок).'
                                            ' Код состоит из 3 латинских букв, имя только из латинских букв, '
                                            'символ это один и более знаков')

        return self.ENTER_FIELDS

    async def add_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        currency_data = update.message.text
        if not self._is_valid_currency_input(currency_data):
            await bot.send_message(chat_id=update.effective_chat.id, text='Неправильные данные\U0001F937')
            return self.END
        code, name, sign = self._get_data_from_input(currency_data)

        try:
            async with self.api_session() as api:
                added = await api.currency_exchange_add_currency(name, code, sign,
                                                                 _request_timeout=self.api_settings.request_timeout)
        except apiexc.ConflictException:
            await bot.send_message(chat_id=update.effective_chat.id,
                                   text='Валюта с таким кодом уже есть\U0001F611')
            return self.END

        msg = html.escape(make_currencies_table([(added.code, added.name, added.sign)]))
        await bot.send_message(chat_id=update.effective_chat.id,
                               text=f'Добавлено\U0001F44C\n<pre>{msg}</pre>',
                               parse_mode=telegram.constants.ParseMode.HTML)
        return self.END

    def _is_valid_currency_input(self, currency_data: str):
        return bool(re.fullmatch(self._input_pattern, currency_data))

    def _get_data_from_input(self, currency_data: str) -> tuple:
        return re.match(self._input_pattern, currency_data).groups()


class BaseExchangeRateConversationCallbacks(BaseCallback, BaseTextConversationCallbacks):
    ENTER_FIELDS = 1

    _input_pattern = re.compile('^ *([a-zA-z]{3}), +([a-zA-z]{3}), +(-?\\d+|\\d+\\.\\d+) *$')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Отправь коды валют и курс в формате <код, код, значение_курса> (без скобок).'
                                            ' Код состоит из 3 латинских букв, имя только из латинских букв, символ')

        return self.ENTER_FIELDS

    def _is_valid_exchange_rate_input(self, currency_data: str):
        return bool(re.fullmatch(self._input_pattern, currency_data))

    def _is_valid_rate(self, rate: float):
        return rate > 0

    def _get_data_from_input(self, currency_data: str) -> tuple:
        return re.match(self._input_pattern, currency_data).groups()


class AddExchangeRateConversationCallbacks(BaseExchangeRateConversationCallbacks):

    async def add_exchange_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        currency_data = update.message.text
        if not self._is_valid_exchange_rate_input(currency_data):
            await bot.send_message(chat_id=update.effective_chat.id, text='Неправильные данные\U0001F937')
            return self.END
        base, target, rate = self._get_data_from_input(currency_data)
        if not self._is_valid_rate(float(rate)):
            await bot.send_message(chat_id=update.effective_chat.id, text='Это как так: курс должен быть строго '
                                                                    'положительным и больше 0🤔')
            return self.END

        try:
            async with self.api_session() as api:
                added = await api.currency_exchange_add_exchange_rate(base, target, float(rate),
                                                                      _request_timeout=self.api_settings.request_timeout)
        except apiexc.ConflictException:
            await bot.send_message(chat_id=update.effective_chat.id,
                                   text='Такой курс уже имеется\U0001F611')
        except apiexc.NotFoundException:
            await bot.send_message(chat_id=update.effective_chat.id,
                                   text='Одна или обе из валют мне неизвестны😇 Может стоит добавить?...')
            return self.END

        msg = html.escape(
            make_exchange_rates_table([(added.base_currency.code, added.target_currency.code, added.rate)])
        )
        await bot.send_message(chat_id=update.effective_chat.id,
                               text=f'Добавлено\U0001F44C\n<pre>{msg}</pre>',
                               parse_mode=telegram.constants.ParseMode.HTML)
        return self.END


class UpdateExchangeRateConversationCallbacks(BaseExchangeRateConversationCallbacks):

    async def update_exchange_rate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        currency_data = update.message.text.upper()
        if not self._is_valid_exchange_rate_input(currency_data):
            await bot.send_message(chat_id=update.effective_chat.id, text='Неправильные данные\U0001F937')
            return self.END

        base, target, rate = self._get_data_from_input(currency_data)
        if not self._is_valid_rate(float(rate)):
            await bot.send_message(chat_id=update.effective_chat.id, text='Это как так: курс должен быть строго '
                                                                    'положительным и больше 0🤔')
            return self.END

        try:
            async with self.api_session() as api:
                updated = await api.currency_exchange_update_exchange_rate(
                    f'{base}{target}', float(rate), _request_timeout=self.api_settings.request_timeout
                )
        except apiexc.NotFoundException:
            await bot.send_message(chat_id=update.effective_chat.id,
                                   text='Такого курса нет, чтобы его менять🧐')
            return self.END

        msg = html.escape(
            make_exchange_rates_table([(updated.base_currency.code, updated.target_currency.code, updated.rate)])
        )
        await bot.send_message(chat_id=update.effective_chat.id,
                               text=f'Изменено\U0001F44C\n<pre>{msg}</pre>',
                               parse_mode=telegram.constants.ParseMode.HTML)
        return self.END


class ConvertCurrencyConversationCallbacks(BaseCallback, BaseTextConversationCallbacks):

    ENTER_BASE, ENTER_TARGET, ENTER_AMOUNT = range(3)

    _currency_code_pattern = CURRENCY_CODE_PATTERN
    _currency_amount_pattern = CURRENCY_AMOUNT_PATTERN
    _invalid_code_entered_msg = 'Неправильный код🤨'

    _user_codes: dict[int, list[str]]

    def __init__(self, *args, **kwargs):
        self._user_codes = {}
        super().__init__(*args, **kwargs)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Отправь конвертируемую валюту (код из 3 латинских букв)')
        self._user_codes[update.effective_user.id] = []

        return self.ENTER_BASE

    async def receive_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        bot = context.bot
        code = update.message.text.upper()
        if not self._is_valid_currency_code(code):
            await bot.send_message(chat_id=update.effective_chat.id, text=self._invalid_code_entered_msg)
            return self.END

        try:
            async with self.api_session() as api:
                await api.currency_exchange_get_currency(code, _request_timeout=self.api_settings.request_timeout)
        except apiexc.NotFoundException:
            await bot.send_message(chat_id=update.effective_chat.id, text='Сожалею, но такая валюта мне неизвестна☹')
            return self.END

        self._user_codes[user_id].append(code)

        if len(self._user_codes[user_id]) == 2:
            await bot.send_message(chat_id=update.effective_chat.id, text='Отправь количество конвертируемой валюты')
            return self.ENTER_AMOUNT
        else:
            await bot.send_message(chat_id=update.effective_chat.id, text='Отправь валюту, в '
                                                                          'которую нужно конвертировать')
            return self.ENTER_TARGET

    async def receive_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        try:
            amount = float(update.message.text)
            if not self._is_valid_amount_input(amount):
                raise ValueError
        except ValueError:
            await bot.send_message(chat_id=update.effective_chat.id, text='Неправильное количество🧐')
            return self.END

        try:
            async with self.api_session() as api:
                base, target = self._user_codes[update.effective_user.id]
                converted = await api.currency_exchange_convert_currencies(
                    base, target, amount, _request_timeout=self.api_settings.request_timeout
                )
        except apiexc.NotFoundException:
            await bot.send_message(chat_id=update.effective_chat.id, text='Извини, но я не знаю такого курса☹')

        answer = (f'Вот:*\n{converted.amount} {converted.base_currency.code} = '
                  f'{converted.converted_amount} {converted.target_currency.code}*, '
                  f'значение курса *{converted.rate}*')
        await bot.send_message(chat_id=update.effective_chat.id, text=answer,
                               parse_mode=telegram.constants.ParseMode.MARKDOWN)
        return self.END

    def _is_valid_currency_code(self, currency_code: str):
        return bool(re.fullmatch(self._currency_code_pattern, currency_code))

    def _is_valid_amount_input(self, amount: float):
        return amount > 0


class AdminAllowedCallbackMixin:

    _admins_rec: AdminsRecord

    def is_request_from_admin(self, update: Update) -> bool:
        return update.effective_user.id in self._admins_rec.read_ids()


class RevokeTokensCallback(BaseCallback, AdminAllowedCallbackMixin):

    def __init__(self, tokens_service: AccessTokenService, admins_rec: AdminsRecord, *args, **kwargs):
        self._tokens_service = tokens_service
        self._admins_rec = admins_rec
        super().__init__(*args, **kwargs)

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_request_from_admin(update):
            return

        async with self.api_session() as api:
            revoked = await api.auth_revoke_users_token(_request_timeout=self.api_settings.request_timeout)

        self._tokens_service.remove_all_tokens()
        self._tokens_service.invalidate_cached_access_token()

        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Revoked {len(revoked.revoked)} tokens')


class ExpungeTokensCallback(AdminAllowedCallbackMixin):

    def __init__(self, tokens_service: AccessTokenService, admins_rec: AdminsRecord):
        self._tokens_service = tokens_service
        self._admins_rec = admins_rec

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_request_from_admin(update):
            return
        self._tokens_service.remove_all_tokens()
        self._tokens_service.invalidate_cached_access_token()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'All tokens removed')


class ErrorHandler:

    def __init__(self, admins_records: AdminsRecord, settings: TgBotSettings):
        self._settings = settings
        self._admins_record = admins_records

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error("Exception while handling an update:", exc_info=context.error)

        if self._settings.notify_admins_on_error:
            await self._notify_all_admins(update, context)

        await context.bot.send_message(update.effective_chat.id,
                                       'Технические неполадки, не удалось обработать твой запрос\U0001F614. '
                                       'Но позже попробуй еще разок!')

    async def _notify_all_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_chat_ids = self._admins_record.read_ids()
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = "".join(tb_list)

        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            "An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
            f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )

        for chat_id in admin_chat_ids:
            await context.bot.send_message(
                chat_id=chat_id, text=message, parse_mode=telegram.constants.ParseMode.HTML
            )
