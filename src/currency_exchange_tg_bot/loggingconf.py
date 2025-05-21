import logging
import sys

from currency_exchange_tg_bot.ioc import bot_settings


def info_and_below_logrecord_filter(logrecord: logging.LogRecord):
	if logrecord.levelno > logging.INFO:
		return False
	return True

def silence_httpx_and_httpcore_logs_filter(logrecord: logging.LogRecord):
	if logrecord.name in ('httpx', 'httpcore'):
		return False
	return True


LOGGING_CONF = {
	"version": 1,
	"disable_existing_loggers": False,
	"formatters": {
		"standard": {
			"format": "%(asctime)s %(name)s (%(levelname)s): %(message)s",
			"datefmt": "%Y-%m-%d %H:%M:%S",
		}
	},
	"handlers": {
		"to_stdout": {
			"level": "DEBUG",
			"class": "logging.StreamHandler",
			"formatter": "standard",
			"stream": sys.stdout,
			"filters": [info_and_below_logrecord_filter, silence_httpx_and_httpcore_logs_filter],
		},
		"to_stderr": {
			"level": "WARNING",
			"class": "logging.StreamHandler",
			"formatter": "standard",
			"stream": sys.stderr,
		},
	},
	"root": {
		"handlers": ["to_stdout", "to_stderr"],
		"level": bot_settings.log_level,
	},
}
