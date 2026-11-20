"""Матрица прав из технического задания."""
from repositories import users
from services.validators import ValidationError

ALL_ROLES = ("client", "employee", "admin")
STAFF = ("employee", "admin")
ROLE_NAMES = dict(zip(ALL_ROLES, ("Пользователь", "Работник", "Администратор")))
RIGHTS = {
    "login": ("Вход в систему", ALL_ROLES),
    "register": ("Самостоятельная регистрация", ("client",)),
    "catalog": ("Просмотр, поиск и фильтрация каталога", ("client",)),
    "favorites": ("Работа с избранным", ("client",)),
    "cart": ("Работа с корзиной и оформление заказов", ("client",)),
    "own_orders": ("Просмотр и удаление своих заказов", ("client",)),
    "profile": ("Просмотр и редактирование профиля", ALL_ROLES),
    "products": ("Управление товарами", STAFF),
    "orders": ("Управление заказами", STAFF),
    "suppliers": ("Управление поставщиками", STAFF),
    "view_users": ("Просмотр пользователей", ("admin",)),
    "create_staff": ("Создание работников и администраторов", ("admin",)),
    "edit_users": ("Редактирование, блокировка и удаление пользователей", ("admin",)),
    "receipt": ("Сохранение чека по заказу", ALL_ROLES),
}


def allowed(role, action):
    return action in RIGHTS and role in RIGHTS[action][1]


def require(user_id, action):
    user = users.get(user_id)
    if not user or user["status"] != "active" or not allowed(user["role"], action):
        raise ValidationError("Недостаточно прав для этой операции")
    return user
