import logging
import os
import sys
import time
from http import HTTPStatus
from sys import stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (CurrentDateError, DictNoneError, EndpointError,
                        EndpointStatusError, HomeworksListError,
                        ResponseJsonError, ResponseKeyError,
                        ResponseStatusError, SendMessageError)

load_dotenv()

# Токен практикума
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
# Токен телеграма
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
# ID чата
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Временной интервал запросов
RETRY_TIME = 600
# URL для запроса статуса домашки
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
# Константа для аутентификации
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

# Словарь статусов домашки для формирования сообщений
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(
    stdout
)
handler.setLevel(logging.INFO)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, [%(levelname)s], %(funcName)s, %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения ботом в телеграм."""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    if not bot.send_message:
        raise SendMessageError('Ошибка! Сообщение не отправлено.')
    logger.info('Сообщение отправлено: %s.', message)


def get_api_answer(current_timestamp):
    """Запрос на сервер с возвратом типа данных Python."""
    logger.info('Отправляем запрос на сервер.')
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    if not ENDPOINT:
        raise EndpointError('Не указан URL сервера для запроса.')
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK.value:
        raise EndpointStatusError(
            'Сервер: %s - не отвечает.\n Headers: %s,\n params: %s,'
            '\n HTTPStatus: %s.' % (
                ENDPOINT,
                HEADERS,
                params,
                response.status_code
            )
        )
    try:
        return response.json()
    except Exception:
        raise ResponseJsonError('Ошибка преобразования данных json()')


def check_response(response):
    """Проверка типа данных, полученных из ответа сервера."""
    logger.info('Проверка данных, полученных из ответа сервера.')
    if not isinstance(response, dict):
        raise TypeError('Тип данных не соответствует ожидаемому.')
    if not isinstance(response.get('homeworks'), list):
        raise HomeworksListError('Получена домашка не в виде списка.')
    if not response:
        raise DictNoneError('Отсутствуют данные в словаре.')
    if not response.get('current_date'):
        raise CurrentDateError('В словаре отсутствует ключ: "current_date".')
    homeworks = response.get('homeworks')
    return homeworks


def parse_status(homework):
    """Парсинг имени домашки и статуса."""
    if len(homework['homework_name']) == 0 or len(homework['status']) == 0:
        raise ResponseKeyError('Отсутствуют запрашиваемые ключи в ответе API.')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise ResponseStatusError(
            'Полученный ключ не числится в списке задокументированных.'
        )
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия элементов окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previous_error = {}
    current_error = {}
    if not check_tokens():
        logger.critical('Отсутствуют обязательные переменные окружения.')
        sys.exit('Отсутствуют обязательные переменные окружения.')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            hw_timestamp = response.get('current_date')
            if not check_response(response):
                logger.debug('Отсутствуют новые статусы в ответе API.')
                logger.info('Список домашних работ пуст.')
            else:
                homeworks = check_response(response)
                homework = homeworks[0]
                homework_verdict = parse_status(homework)
                send_message(bot, homework_verdict)
            current_timestamp = hw_timestamp
        except telegram.TelegramError as error:
            message = f'Сбой при отправке сообщения: {error}'
            logger.exception(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(message)
            current_error['message'] = message
            if previous_error != current_error:
                send_message(bot, message)
                previous_error = current_error.copy()
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
