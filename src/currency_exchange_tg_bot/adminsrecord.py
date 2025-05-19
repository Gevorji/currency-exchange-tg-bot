from currency_exchange_tg_bot.config import TgBotSettings


class AdminsRecord:
    """
    Records file is a file with utf-8 encoded text content of format <id,id,id,...id,id>
    (angle brackets only for representation)
    """

    def __init__(self, settings: TgBotSettings):
        self._records_file = settings.admin_records_file

    def read_ids(self) -> list[int]:
        with open(self._records_file, 'r', encoding='utf-8') as f:
            return [int(id_str) for id_str in f.read().strip('\n').split(',') if id_str]
