Телеграм бот является компонентом (фронтендом) 
[проекта "Обменник валют"](https://github.com/Gevorji/currency-exchange-fapi).

Для запуска соберите образ docker:
`docker build -t curexch_tgbot -f ./docker/Dockerfile.currencyexchangetgbot .`

и запустите контейнер:  
`docker run --rm -d --env-file .env -v ./admin_records:/home/tgbot/admin_records
 curexch_tgbot`

Здесь мы сделали 2 важные вещи: дали контейнеру переменные окружения через файл .env при помощи опции --env-file, 
а также смонтировали в контейнер файл admin_records (без него проект не запустится).

## Файл admin_records
Файл имеет текстовое содержание, формат - id чатов администраторов, 
разделенные запятой (например `123452,242343,145432`).  
В чаты администраторов присылаются логи и отчеты об ошибках, возникших в боте, а также
им показываются дополнительные команды, связанные с доступом к API сервиса обмена валют.

## Переменные окружения в файле .env
`TG_BOT_TOKEN` - [телеграм токен бота](https://core.telegram.org/bots#how-do-i-create-a-bot)
`CURRENCY_EXCHANGE_HOST` - базовая часть url для обращения к сервису обмена валют 
(схема+хост+порт, например http://localhost:80) 
`CURRENCY_EXCHANGE_USERNAME` - имя пользователя API сервиса обменника валют (см. раздел о регистрации клиентов API).
`CURRENCY_EXCHANGE_PASSWORD` - пароль пользователя API сервиса обменника валют.
