"""Регистрация, вход, профиль и администрирование учётных записей."""
import bcrypt
from psycopg2.errors import ForeignKeyViolation, RestrictViolation, UniqueViolation

from repositories import users
from services.permissions import ALL_ROLES, STAFF, require
from services.validators import (
    ValidationError, validate_email, validate_password, validate_phone, validate_required,
)


def hash_password(password):
    return bcrypt.hashpw(validate_password(password).encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _create(email, password, name, phone=None, role="client"):
    email = validate_email(email)
    try:
        return users.create(
            email, hash_password(password), validate_required(name, "Имя"),
            validate_phone(phone), role,
        )
    except UniqueViolation as exc:
        raise ValidationError("Эта электронная почта уже зарегистрирована") from exc


def register(email, password, confirmation, consent):
    email = validate_email(email)
    if password != confirmation:
        raise ValidationError("Пароли не совпадают")
    if not consent:
        raise ValidationError("Подтвердите согласие на обработку персональных данных")
    return _create(email, password, email.split("@", 1)[0])


def login(email, password):
    email = validate_email(email)
    if not password or len(password.encode("utf-8")) > 72:
        raise ValidationError("Неверная электронная почта или пароль")
    user = users.find_by_email(email)
    if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("ascii")):
        raise ValidationError("Неверная электронная почта или пароль")
    if user["status"] == "blocked":
        raise ValidationError("Учётная запись заблокирована. Обратитесь к администратору")
    del user["password_hash"]
    return user


def save_profile(user_id, name, phone, avatar_path):
    require(user_id, "profile")
    profile = users.update_profile(
        user_id, validate_required(name, "Имя"), validate_phone(phone), avatar_path,
    )
    if not profile:
        raise ValidationError("Учётная запись недоступна")
    return profile


def create_staff(actor_id, email, password, name, phone, role):
    require(actor_id, "create_staff")
    if role not in STAFF:
        raise ValidationError("Выберите роль работника или администратора")
    return _create(email, password, name, phone, role)


def list_users(actor_id, role=None, search=""):
    require(actor_id, "view_users")
    return users.list_users(role, search)


def edit_user(actor_id, user_id, name, phone, role, status, password=""):
    require(actor_id, "edit_users")
    if role not in ALL_ROLES or status not in ("active", "blocked"):
        raise ValidationError("Выберите роль и статус учётной записи")
    users.change(
        actor_id, user_id, name=validate_required(name, "Имя"), phone=validate_phone(phone),
        role=role, status=status, password_hash=hash_password(password) if password else None,
    )


def delete_user(actor_id, user_id):
    require(actor_id, "edit_users")
    try:
        users.change(actor_id, user_id, remove=True)
    except (ForeignKeyViolation, RestrictViolation) as exc:
        raise ValidationError("У пользователя есть заказы. Вместо удаления его можно заблокировать") from exc
