
from telegram.ext import Application

from currency_exchange_tg_bot.bothandlers import handlers
from currency_exchange_tg_bot.botcommands import get_commands_and_scopes
from currency_exchange_tg_bot.ioc import admins_rec, bot_settings, error_handler


scoped_commands = get_commands_and_scopes(admins_rec.read_ids()) # used with Bot.set_my_commands

async def app_post_init(app: Application):
    for scope, commands in scoped_commands:
        await app.bot.set_my_commands(commands, scope)


def main():
    application = Application.builder().token(bot_settings.tg_bot_token).build()

    application.add_handlers(handlers)
    application.add_error_handler(error_handler)

    application.post_init = app_post_init

    application.run_polling()

if __name__ == '__main__':
    main()
