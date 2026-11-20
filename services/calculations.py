"""Расчёты корзины, заказа и чека в Decimal."""
from decimal import Decimal


def line_total(price, quantity):
    return price * quantity


def totals(items):
    return (
        sum(item["quantity"] for item in items),
        sum((line_total(item["price"], item["quantity"]) for item in items), Decimal("0.00")),
    )
