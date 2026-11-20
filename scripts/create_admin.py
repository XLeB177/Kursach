"""Создание учётной записи сотрудника из командной строки."""
from argparse import ArgumentParser
from getpass import getpass

from psycopg2 import Error

from services.auth import _create


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("name")
    parser.add_argument("--role", choices=("admin", "employee"), default="admin")
    args = parser.parse_args()
    password = getpass("Пароль: ")
    if getpass("Подтверждение пароля: ") != password:
        parser.exit(1, "Пароли не совпадают\n")
    try:
        _create(args.email, password, args.name, role=args.role)
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")
    except Error:
        parser.exit(1, "Ошибка PostgreSQL. Проверьте подключение и создание таблиц.\n")
    print("Учётная запись создана")


if __name__ == "__main__":
    main()
