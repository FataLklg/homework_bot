import logging
import os
import time
from http import HTTPStatus
from sys import stdout

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (DictNoneError, EndpointError, EndpointStatusError,
                        HomeworksListError, ResponseKeyError,
                        ResponseStatusError)

load_dotenv()

# Токен практикума
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
# Токен телеграма
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
# ID чата
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Временной интервал запросов
RETRY_TIME = 100
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
    '%(asctime)s, [%(levelname)s], %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения ботом в телеграм."""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logger.info(f'Сообщение отправлено: "{message}".')


def get_api_answer(current_timestamp):
    """Запрос на сервер с возвратом типа данных Python."""
    logger.info('Отправляем запрос на сервер.')
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    if not ENDPOINT:
        raise EndpointError('Не указан URL сервера для запроса.')
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK.value:
        raise EndpointStatusError('Сервер не отвечает.')
    return response.json()


def check_response(response):
    """Проверка типа данных, полученных из ответа сервера."""
    if not isinstance(response, dict):
        raise TypeError('Тип данных не соответствует ожидаемому.')
    if not isinstance(response.get('homeworks'), list):
        raise HomeworksListError('Получена домашка не в виде списка.')
    if response == {}:
        raise DictNoneError('Отсутствуют данные в словаре.')
    return response.get('homeworks')


def parse_status(homework):
    """Парсинг имени домашки и статуса."""
    if not homework['homework_name'] or not homework['status']:
        raise ResponseKeyError('Отсутствуют запрашиваемые ключи в ответе API.')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise ResponseStatusError(
            'Полученный ключ не числится в списке задокументированных.'
        )
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия элементов окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    logger.critical('Отсутствуют обязательные переменные окружения.')
    return False


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previous_error = {}
    current_error = {}
    if check_tokens():
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
