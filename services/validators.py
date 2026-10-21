"""Проверка вводимых данных. Правила — раздел 9 AGENTS.md.

Каждая функция возвращает очищенное значение или вызывает ValidationError
с понятным пользователю сообщением на русском.
"""
import re
from decimal import Decimal

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PHONE_CHARS_RE = re.compile(r"\+?[\d\s()\-]+")
NUMBER_RE = re.compile(r"-?\d+(\.\d+)?")
INT_RE = re.compile(r"-?\d+")

EMAIL_MAX_LEN = 254
PASSWORD_MIN_LEN = 6
PASSWORD_MAX_BYTES = 72  # ограничение bcrypt
PRICE_MAX = Decimal("99999999.99")  # предел NUMERIC(10,2)
QUANTITY_MAX = 1_000_000


class ValidationError(ValueError):
    """Ошибка проверки данных. Текст можно показывать пользователю."""


def validate_required(value, field_name):
    """Обязательное текстовое поле: не пустое и не из одних пробелов."""
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValidationError(f"Поле «{field_name}» обязательно для заполнения")
    return text


def validate_email(value):
    """Почта: формат «имя@домен.зона», возвращается в нижнем регистре."""
    email = validate_required(value, "Электронная почта").lower()
    if len(email) > EMAIL_MAX_LEN or not EMAIL_RE.fullmatch(email):
        raise ValidationError("Введите корректный адрес электронной почты")
    return email


def validate_password(value):
    """Пароль: не короче 6 символов и не длиннее 72 байт (предел bcrypt)."""
    if value is None or value == "":
        raise ValidationError("Введите пароль")
    if len(value) < PASSWORD_MIN_LEN:
        raise ValidationError(
            f"Пароль слишком короткий: минимум {PASSWORD_MIN_LEN} символов"
        )
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValidationError("Пароль слишком длинный")
    return value


def validate_phone(value):
    """Телефон необязателен. Если указан: 10–15 цифр, допустимы + пробелы ( ) -.

    Пустое значение возвращает None.
    """
    if value is None:
        return None
    phone = str(value).strip()
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not PHONE_CHARS_RE.fullmatch(phone) or not 10 <= len(digits) <= 15:
        raise ValidationError(
            "Телефон должен содержать от 10 до 15 цифр "
            "(допустимы знаки +, пробелы, скобки и дефисы)"
        )
    return phone


def validate_price(value):
    """Цена: число не меньше 0, не более двух знаков после запятой."""
    if value is None or isinstance(value, bool) or str(value).strip() == "":
        raise ValidationError("Введите цену")
    text = str(value).strip().replace(",", ".")
    if not NUMBER_RE.fullmatch(text):
        raise ValidationError("Цена должна быть числом")
    price = Decimal(text)
    if price < 0:
        raise ValidationError("Цена не может быть отрицательной")
    if price.as_tuple().exponent < -2:
        raise ValidationError("В цене допустимо не более двух знаков после запятой")
    if price > PRICE_MAX:
        raise ValidationError("Слишком большая цена")
    return price.quantize(Decimal("0.01"))


def validate_quantity(value):
    """Количество: целое число не меньше 0."""
    if value is None or isinstance(value, bool) or str(value).strip() == "":
        raise ValidationError("Введите количество")
    text = str(value).strip()
    if not INT_RE.fullmatch(text):
        raise ValidationError("Количество должно быть целым числом")
    quantity = int(text)
    if quantity < 0:
        raise ValidationError("Количество не может быть отрицательным")
    if quantity > QUANTITY_MAX:
        raise ValidationError("Слишком большое количество")
    return quantity
