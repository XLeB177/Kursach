"""Каталог, товары и поставщики с проверкой прав и данных."""
from psycopg2.errors import ForeignKeyViolation, RestrictViolation

from repositories import catalog, suppliers
from services.permissions import require
from services.validators import (
    ValidationError, validate_email, validate_phone, validate_price, validate_quantity,
    validate_required,
)

SUPPLIER_STATUSES = ("Активный", "Неактивный")


def read_categories(actor_id, staff=False):
    require(actor_id, "products" if staff else "catalog")
    return catalog.categories()


def browse(actor_id, *, favorite=False, **filters):
    require(actor_id, "favorites" if favorite else "catalog")
    return catalog.products(favorite_id=actor_id if favorite else None, **filters)


def favorite_ids(actor_id):
    require(actor_id, "favorites")
    return catalog.favorite_ids(actor_id)


def toggle_favorite(actor_id, product_id, checked):
    require(actor_id, "favorites")
    try:
        catalog.save_favorite(actor_id, product_id, checked)
    except ForeignKeyViolation as exc:
        raise ValidationError("Товар больше недоступен") from exc


def list_products(actor_id, **filters):
    require(actor_id, "products")
    return catalog.products(name_only=True, **filters)


def save_product(actor_id, fields, product_id=None):
    require(actor_id, "products")
    minimum = validate_quantity(fields["players_min"])
    maximum = validate_quantity(fields["players_max"])
    duration = validate_quantity(fields["play_time"])
    if minimum < 1 or maximum < minimum:
        raise ValidationError("Укажите корректный диапазон количества игроков")
    if duration < 1:
        raise ValidationError("Время игры должно быть больше нуля")
    if not fields["category_id"]:
        raise ValidationError("Выберите категорию товара")
    try:
        saved = catalog.save_product((
            validate_required(fields["name"], "Название"),
            validate_required(fields["description"], "Описание"), validate_price(fields["price"]),
            validate_quantity(fields["quantity"]), fields["image_path"], fields["category_id"],
            minimum, maximum, duration, validate_quantity(fields["age"]),
        ), product_id)
    except ForeignKeyViolation as exc:
        raise ValidationError("Категория больше недоступна") from exc
    if saved is None:
        raise ValidationError("Товар не найден")
    return saved


def delete_product(actor_id, product_id):
    require(actor_id, "products")
    try:
        catalog.delete_product(product_id)
    except (ForeignKeyViolation, RestrictViolation) as exc:
        raise ValidationError("Товар есть в заказах. Вместо удаления укажите остаток 0") from exc


def list_suppliers(actor_id, search="", status=None):
    require(actor_id, "suppliers")
    return suppliers.list_suppliers(search.strip(), status)


def save_supplier(actor_id, name, email, phone, status, product_ids, supplier_id=None):
    require(actor_id, "suppliers")
    if status not in SUPPLIER_STATUSES:
        raise ValidationError("Выберите статус поставщика")
    try:
        suppliers.save((
            validate_required(name, "Название"), validate_email(email),
            validate_required(validate_phone(phone), "Телефон"), status,
        ), product_ids, supplier_id)
    except ForeignKeyViolation as exc:
        raise ValidationError("Один из товаров больше недоступен") from exc


def delete_supplier(actor_id, supplier_id):
    require(actor_id, "suppliers")
    suppliers.delete(supplier_id)
