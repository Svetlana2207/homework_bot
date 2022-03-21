
import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram.error import TelegramError

import exceptions as err

load_dotenv()

logging.basicConfig(
    filename='logg.log',
    filemode='a',
    format=('%(asctime)s '
            '%(levelname)s '
            '%(message)s '
            '%(funcName)s '
            '%(lineno)d'),
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщений в телеграм-чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except TelegramError:
        logger.error(f'не получается отправить в {TELEGRAM_CHAT_ID}')


def get_api_answer(current_timestamp):
    """Запрос к эндпойнту каждые 10 минут."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as e:
        logger.error('URL недоступен')
        raise SystemExit(e, 'URL недоступен')
    if response.status_code != HTTPStatus.OK:
        logger.error(f'код ответа сервера не соответствует.\
                      Код ответа API {response.status_code}')
        raise err.ResponseStatusIsNotOK(f'код ответа сервера\
            не соответствует.Код отввета API {response.status_code}')
    elif response.status_code == HTTPStatus.OK:
        try:
            response = response.json()
            return response
        except json.decoder.JSONDecodeError:
            logger.error('ответ API не преобразуется в Json')
    else:
        logger.error('другие сбои эндпойнта')
        raise err.ResponseStatusIsNotOK('другие сбои эндпойнта')


def check_response(response):
    """Проверка API на корректность ответа."""
    if type(response) is not dict:
        raise TypeError('формат ответа АPI должен быть словарем')
    elif 'homeworks' not in response:
        raise KeyError('нет ключа "homeworks" в ответе API')
    elif 'current_date' not in response:
        raise KeyError('нет ключа "current_date" в ответе API')
    elif type(response['current_date']) is not int:
        raise TypeError('формат времени ответа API должно быть числом')
    elif type(response['homeworks']) is not list:
        raise TypeError('формат домашки в ответе API должен быть списком')
    homework = response['homeworks']

    return homework


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    if 'homework_name' not in homework:
        logger.error('отсутствует "homework_name" в ответе API')
        raise KeyError('отсутствует "homework_name" в ответе API')
    if 'status' not in homework:
        logger.error('отсутствует "homework_status" в ответе API')
        raise KeyError('отсутствует "status" в ответе API')
    if homework['status'] not in HOMEWORK_STATUSES:
        logging.error('недокументированный статус в ответе API')
        raise KeyError('недокументированный статус в ответе API')

    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}".\
                                                   {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    ENV_VARS = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(ENV_VARS)


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
    else:
        logger.critical('отсутствует переменная окружения')
        raise err.NoEnvironmentVariable('отсутствует переменная окружения')

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logger.info('нет изменений статуса домашней работы')
            else:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
                logger.info(f'отправка сообщения в Telegram "{message}"')

            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
