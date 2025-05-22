from telegram import BotCommandScopeChat, BotCommandScope, BotCommandScopeDefault

default_commands = [
    ('allcurrencies', 'Показать все валюты, известные боту'),
    ('allexchangerates', 'Показать все обменные курсы, известные боту'),
    ('showcurrency', 'Показать определенную валюту'),
    ('showexchangerate', 'Показать определенный обменный курс'),
    ('addcurrency', 'Добавить валюту'),
    ('addexchangerate', 'Добавить обменный курс'),
    ('editexchangerate', 'Поменять значение обменного курса'),
    ('convertcurrency', 'Конвертировать валюту'),
]

admin_user_commands = [
    ('revoketokens', 'Сделать все имеющиеся у приложения бота токены сервиса недействительными и забыть их'),
    ('expungetokens', 'Забыть все имеющиеся у приложения бота токены сервиса')
]


def get_admin_chats_command_scopes(chat_ids: list[int]) -> list[BotCommandScopeChat]:
    return [BotCommandScopeChat(chat_id) for chat_id in chat_ids]

def get_commands_and_scopes(admin_chat_ids: list[int]) -> list[tuple[BotCommandScope, list[tuple[str, str]]]]:
    default = [(BotCommandScopeDefault(), default_commands)]
    admins_scopes = get_admin_chats_command_scopes(admin_chat_ids)
    admins = [(comscope, admin_user_commands + default_commands) for comscope in admins_scopes]
    return default + admins