"""Права и правила работы с корзиной и заказами."""
from repositories import orders
from services.permissions import require
from services.validators import ValidationError, validate_quantity


def get_cart(actor_id):
    require(actor_id, "cart")
    return orders.cart(actor_id)


def change_cart(actor_id, product_id, quantity, *, add=False):
    require(actor_id, "cart")
    quantity = validate_quantity(quantity)
    if add and quantity == 0:
        raise ValidationError("Укажите количество от 1")
    orders.set_cart(actor_id, product_id, quantity, add=add)


def clear_cart(actor_id):
    require(actor_id, "cart")
    orders.clear_cart(actor_id)


def checkout(actor_id):
    require(actor_id, "cart")
    return orders.create(actor_id)


def list_orders(actor_id, own=False, **filters):
    require(actor_id, "own_orders" if own else "orders")
    return orders.list_orders(user_id=actor_id if own else None, **filters)


def clients(actor_id):
    require(actor_id, "orders")
    return orders.client_options()


def detail(actor_id, order_id):
    require(actor_id, "orders")
    return orders.detail(order_id)


def _quantities(items):
    result = {}
    for product_id, value in items:
        quantity = validate_quantity(value)
        if quantity == 0:
            raise ValidationError("Укажите количество от 1")
        result[product_id] = validate_quantity(result.get(product_id, 0) + quantity)
    return result


def create(actor_id, user_id, items):
    require(actor_id, "orders")
    return orders.create(user_id, _quantities(items))


def edit(actor_id, order_id, status, items=None):
    require(actor_id, "orders")
    orders.edit(order_id, status, _quantities(items) if items is not None else None)


def delete(actor_id, order_id, own=False):
    require(actor_id, "own_orders" if own else "orders")
    orders.delete(order_id, owner_id=actor_id if own else None)
