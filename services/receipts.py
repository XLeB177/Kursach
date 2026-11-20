"""Получение данных чека с проверкой владельца заказа."""
from repositories import orders
from services.permissions import require
from services.receipt_pdf import write_receipt


def save(actor_id, order_id, target):
    actor = require(actor_id, "receipt")
    owner_id = actor_id if actor["role"] == "client" else None
    order, items = orders.detail(order_id, owner_id=owner_id)
    write_receipt(order, items, target)
