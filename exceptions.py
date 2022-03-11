class NoMoneyNoPower(Exception):
    """Статус начинающего."""


class ResponseStatusIsNotOK(Exception):
    """Статус ответа сервера отличный от `OК`."""


class NoSendMessage(Exception):
    """Сообщение не отправлено."""


class NoEnvironmentVariable(Exception):
    """Отсутствует переменная окружения."""
