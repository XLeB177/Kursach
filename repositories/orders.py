"""Корзина, заказы и транзакционные операции с остатками."""
from repositories.common import transaction
from services.calculations import totals
from services.validators import PRICE_MAX, ValidationError

NEW, PROCESSING, DELIVERED = STATUSES = ("Новый", "В обработке", "Доставленный")


def _lock_products(cur, ids):
    cur.execute(
        "SELECT id, name, price, quantity FROM products WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
        (sorted(ids),),
    )
    return {row["id"]: row for row in cur.fetchall()}


def _lock_client(cur, user_id):
    cur.execute("SELECT id FROM users WHERE id=%s AND role='client' AND status='active' FOR UPDATE", (user_id,))
    if not cur.fetchone():
        raise ValidationError("Пользователь недоступен для оформления заказа")


def cart(user_id):
    with transaction() as cur:
        cur.execute(
            """SELECT p.id, p.name, p.price, p.image_path, p.quantity AS stock, c.quantity
               FROM cart_items c JOIN products p ON p.id = c.product_id WHERE c.user_id=%s
               ORDER BY p.name, p.id""",
            (user_id,),
        )
        return cur.fetchall()


def set_cart(user_id, product_id, quantity, *, add=False):
    with transaction() as cur:
        _lock_client(cur, user_id)
        if quantity == 0:
            cur.execute("DELETE FROM cart_items WHERE user_id=%s AND product_id=%s", (user_id, product_id))
            return
        product = _lock_products(cur, [product_id]).get(product_id)
        if not product or product["quantity"] == 0:
            raise ValidationError("Нет в наличии")
        if add:
            cur.execute("SELECT quantity FROM cart_items WHERE user_id=%s AND product_id=%s", (user_id, product_id))
            old = cur.fetchone()
            quantity += old["quantity"] if old else 0
        if quantity > product["quantity"]:
            raise ValidationError(f"Доступно только {product['quantity']} шт.")
        cur.execute(
            """INSERT INTO cart_items (user_id, product_id, quantity) VALUES (%s,%s,%s)
               ON CONFLICT (user_id, product_id) DO UPDATE SET quantity=excluded.quantity""",
            (user_id, product_id, quantity),
        )


def clear_cart(user_id):
    with transaction() as cur:
        _lock_client(cur, user_id)
        cur.execute("DELETE FROM cart_items WHERE user_id=%s", (user_id,))


def client_options():
    with transaction() as cur:
        cur.execute("SELECT id, name, email FROM users WHERE role='client' AND status='active' ORDER BY name, email")
        return cur.fetchall()


def list_orders(user_id=None, search="", status=None, newest=True):
    order = "DESC" if newest else "ASC"
    with transaction() as cur:
        cur.execute(
            f"""SELECT o.id, o.user_id, o.status, o.total, o.created_at, u.name, u.email,
                       COALESCE(string_agg(p.name || ' × ' || oi.quantity, ', ' ORDER BY p.name), '') AS content
                FROM orders o JOIN users u ON u.id=o.user_id
                LEFT JOIN order_items oi ON oi.order_id=o.id LEFT JOIN products p ON p.id=oi.product_id
                WHERE (%s::integer IS NULL OR o.user_id=%s) AND (%s::text IS NULL OR o.status=%s)
                  AND (strpos(o.id::text, %s) > 0 OR strpos(lower(u.name), lower(%s)) > 0
                       OR strpos(lower(u.email), lower(%s)) > 0 OR EXISTS (
                           SELECT 1 FROM order_items i JOIN products pp ON pp.id=i.product_id
                           WHERE i.order_id=o.id AND strpos(lower(pp.name), lower(%s)) > 0))
                GROUP BY o.id, u.id ORDER BY o.created_at {order}, o.id {order}""",
            (user_id, user_id, status, status, search, search, search, search),
        )
        return cur.fetchall()


def detail(order_id, owner_id=None):
    with transaction() as cur:
        cur.execute(
            """SELECT o.*, u.name, u.email FROM orders o JOIN users u ON u.id=o.user_id
               WHERE o.id=%s AND (%s::integer IS NULL OR o.user_id=%s) FOR SHARE OF o""",
            (order_id, owner_id, owner_id),
        )
        order = cur.fetchone()
        if not order:
            raise ValidationError("Заказ не найден или недоступен")
        cur.execute(
            """SELECT i.product_id, p.name, i.quantity, i.price FROM order_items i
               JOIN products p ON p.id=i.product_id WHERE i.order_id=%s ORDER BY p.name, p.id""",
            (order_id,),
        )
        return order, cur.fetchall()


def _save_lines(cur, order_id, quantities, old_items):
    if not quantities:
        raise ValidationError("Добавьте хотя бы одну позицию заказа")
    products = _lock_products(cur, old_items.keys() | quantities.keys())
    lines = []
    for product_id, quantity in quantities.items():
        product = products.get(product_id)
        if not product:
            raise ValidationError("Один из товаров больше недоступен")
        previous = old_items.get(product_id)
        available = product["quantity"] + (previous["quantity"] if previous else 0)
        if quantity > available:
            raise ValidationError(f"Недостаточно товара «{product['name']}». Доступно {available} шт.")
        lines.append({"product_id": product_id, "quantity": quantity,
                      "price": previous["price"] if previous else product["price"]})

    _, total = totals(lines)
    if total > PRICE_MAX:
        raise ValidationError("Сумма заказа превышает допустимый предел")

    deltas = [
        (old_items.get(key, {}).get("quantity", 0) - quantities.get(key, 0), key)
        for key in products
    ]
    cur.executemany("UPDATE products SET quantity=quantity+%s WHERE id=%s", deltas)
    cur.execute("DELETE FROM order_items WHERE order_id=%s", (order_id,))
    cur.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s,%s,%s,%s)",
        [(order_id, row["product_id"], row["quantity"], row["price"]) for row in lines],
    )
    cur.execute("UPDATE orders SET total=%s WHERE id=%s", (total, order_id))


def create(user_id, quantities=None):
    with transaction() as cur:
        _lock_client(cur, user_id)
        checkout = quantities is None
        if checkout:
            cur.execute("SELECT product_id, quantity FROM cart_items WHERE user_id=%s AND quantity > 0", (user_id,))
            quantities = {row["product_id"]: row["quantity"] for row in cur.fetchall()}
        cur.execute("INSERT INTO orders (user_id, status, total) VALUES (%s,%s,0) RETURNING id", (user_id, NEW))
        order_id = cur.fetchone()["id"]
        _save_lines(cur, order_id, quantities, {})
        if checkout:
            cur.execute("DELETE FROM cart_items WHERE user_id=%s", (user_id,))
        return order_id


def _lock_order(cur, order_id, owner_id=None):
    cur.execute(
        """SELECT status FROM orders WHERE id=%s
           AND (%s::integer IS NULL OR user_id=%s) FOR UPDATE""",
        (order_id, owner_id, owner_id),
    )
    order = cur.fetchone()
    if not order:
        raise ValidationError("Заказ не найден или недоступен")
    return order["status"]


def edit(order_id, status, quantities=None):
    with transaction() as cur:
        previous = _lock_order(cur, order_id)
        if status not in STATUSES or STATUSES.index(status) - STATUSES.index(previous) not in (0, 1):
            raise ValidationError("Статус можно изменить только на следующий")
        if quantities is not None:
            if previous != NEW:
                raise ValidationError("Состав можно изменить только у нового заказа")
            cur.execute("SELECT product_id, quantity, price FROM order_items WHERE order_id=%s", (order_id,))
            _save_lines(cur, order_id, quantities, {row["product_id"]: row for row in cur.fetchall()})
        cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))


def delete(order_id, owner_id=None):
    with transaction() as cur:
        status = _lock_order(cur, order_id, owner_id)
        if owner_id is not None and status != NEW:
            raise ValidationError("Удалить можно только новый заказ")
        if status == NEW:
            cur.execute("SELECT product_id, quantity FROM order_items WHERE order_id=%s", (order_id,))
            items = cur.fetchall()
            _lock_products(cur, [row["product_id"] for row in items])
            cur.executemany(
                "UPDATE products SET quantity=quantity+%s WHERE id=%s",
                [(row["quantity"], row["product_id"]) for row in items],
            )
        cur.execute("DELETE FROM orders WHERE id=%s", (order_id,))
