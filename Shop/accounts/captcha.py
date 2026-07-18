"""Простая собственная капча: арифметический вопрос в сессии. Без внешних сервисов.

Параметр key позволяет держать независимые капчи на разных формах
(например, регистрация и форма заявки) в одной сессии.
"""
import random

SESSION_KEY = 'captcha_answer'


def new_captcha(session, key=SESSION_KEY):
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    session[key] = a + b
    return f'{a} + {b}'


def check_captcha(session, value, key=SESSION_KEY):
    try:
        ok = int(str(value).strip()) == int(session.get(key))
    except (TypeError, ValueError):
        return False
    if ok:
        # Одноразовость: решённый ответ нельзя переиспользовать в рамках сессии.
        session.pop(key, None)
    return ok
