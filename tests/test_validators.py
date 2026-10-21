"""Тесты services/validators.py."""
from decimal import Decimal

import pytest

from services.validators import (
    ValidationError,
    validate_email,
    validate_password,
    validate_phone,
    validate_price,
    validate_quantity,
    validate_required,
)


# --- Обязательное поле ---

def test_required_strips_spaces():
    assert validate_required("  Игра  ", "Название") == "Игра"


@pytest.mark.parametrize("value", ["", "   ", None])
def test_required_rejects_empty(value):
    with pytest.raises(ValidationError):
        validate_required(value, "Название")


# --- Почта ---

@pytest.mark.parametrize("value, expected", [
    ("user@example.com", "user@example.com"),
    ("  User@Example.COM ", "user@example.com"),
    ("a.b-c@mail.co.uk", "a.b-c@mail.co.uk"),
])
def test_email_valid(value, expected):
    assert validate_email(value) == expected


@pytest.mark.parametrize("value", [
    "", "   ", None, "userexample.com", "user@", "@example.com",
    "user@example", "us er@example.com", "user@@example.com",
    "a@b.c" + "d" * 260,
])
def test_email_invalid(value):
    with pytest.raises(ValidationError):
        validate_email(value)


# --- Пароль ---

def test_password_min_length_boundary():
    assert validate_password("123456") == "123456"
    with pytest.raises(ValidationError):
        validate_password("12345")


@pytest.mark.parametrize("value", ["", None])
def test_password_empty(value):
    with pytest.raises(ValidationError):
        validate_password(value)


def test_password_max_bytes_boundary():
    assert validate_password("a" * 72) == "a" * 72
    with pytest.raises(ValidationError):
        validate_password("a" * 73)
    # русские буквы занимают по 2 байта: 36 символов можно, 37 нельзя
    assert validate_password("ы" * 36) == "ы" * 36
    with pytest.raises(ValidationError):
        validate_password("ы" * 37)


# --- Телефон ---

@pytest.mark.parametrize("value", [None, "", "   "])
def test_phone_optional(value):
    assert validate_phone(value) is None


@pytest.mark.parametrize("value", [
    "89001234567", "+7 900 123-45-67", "+7 (900) 123-45-67", "1234567890",
    "123456789012345",
])
def test_phone_valid(value):
    assert validate_phone(value) == value


@pytest.mark.parametrize("value", [
    "123456789", "1234567890123456", "abc1234567890", "+7 900 12x-45-67",
    "7+9001234567", "++79001234567",
])
def test_phone_invalid(value):
    with pytest.raises(ValidationError):
        validate_phone(value)


# --- Цена ---

@pytest.mark.parametrize("value, expected", [
    ("0", Decimal("0.00")),
    ("1250", Decimal("1250.00")),
    ("1250.5", Decimal("1250.50")),
    ("1250,50", Decimal("1250.50")),
    (990, Decimal("990.00")),
    (Decimal("10.1"), Decimal("10.10")),
    ("99999999.99", Decimal("99999999.99")),
])
def test_price_valid(value, expected):
    assert validate_price(value) == expected


@pytest.mark.parametrize("value", [
    "", "  ", None, True, "abc", "-1", "-0.01", "12.345", "1e3", "1 250",
    "100000000", "nan",
])
def test_price_invalid(value):
    with pytest.raises(ValidationError):
        validate_price(value)


# --- Количество ---

@pytest.mark.parametrize("value, expected", [
    ("0", 0), ("5", 5), (" 12 ", 12), (7, 7), ("1000000", 1_000_000),
])
def test_quantity_valid(value, expected):
    assert validate_quantity(value) == expected


@pytest.mark.parametrize("value", [
    "", " ", None, True, "abc", "-1", "1.5", "1,5", "1e3", "1000001",
])
def test_quantity_invalid(value):
    with pytest.raises(ValidationError):
        validate_quantity(value)
