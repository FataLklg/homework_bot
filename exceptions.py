class EndpointError(Exception):
    """Исключение отсутствия передачи URL для запроса."""
    pass


class EndpointStatusError(Exception):
    """Исключение недоступности эндпоинта при запросе."""
    pass


class DictNoneError(Exception):
    """Исключение при получении пустого словаря."""
    pass


class HomeworksListError(Exception):
    """Исключение при получении домашки не в виде списка."""
    pass


class ResponseKeyError(Exception):
    """Исключение при отстутствии запрашиваемых ключей в ответе API."""
    pass


class ResponseStatusError(Exception):
    """Исключение при наличии недокументированного статуса в ответе API."""
    pass


class SendMessageError(Exception):
    """Исключение при наличии ошибки во время отправки сообщения."""
    pass


class ResponseJsonError(Exception):
    """Исключение при наличии ошибки во время преобразования типа данных."""
    pass


class CurrentDateError(Exception):
    """Исключение при отсутствии ключа current_date в словаре."""
    pass
