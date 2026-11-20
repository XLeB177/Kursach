"""Запросы каталога, избранного и товаров."""
from repositories.common import transaction

PRODUCT_FIELDS = """p.id, p.name, p.description, p.price, p.quantity, p.image_path,
                   p.category_id, p.players_min, p.players_max, p.play_time, p.age,
                   c.name AS category"""


def categories():
    with transaction() as cur:
        cur.execute("SELECT id, name FROM categories ORDER BY name")
        return cur.fetchall()


def products(search="", category=None, players=None, play_time=None, age=None, price=None,
             favorite_id=None, popular=False, name_only=False, product_id=None):
    conditions, params = [], []

    def add(condition, *values):
        conditions.append(condition)
        params.extend(values)

    search = search.strip()
    if search:
        condition = "strpos(lower(p.name), lower(%s)) > 0"
        if name_only:
            add(condition, search)
        else:
            add(f"({condition} OR strpos(lower(p.description), lower(%s)) > 0)", search, search)
    if category is not None:
        add("p.category_id = %s", category)
    if players is not None:
        if players >= 6:
            add("p.players_max >= %s", players)
        else:
            add("%s BETWEEN p.players_min AND p.players_max", players)
    if play_time is not None:
        minimum, maximum = play_time
        add("p.play_time > %s", minimum)
        if maximum is not None:
            add("p.play_time <= %s", maximum)
    if age is not None:
        add("p.age = %s", age)
    if price is not None:
        minimum, maximum = price
        add("p.price >= %s", minimum)
        if maximum is not None:
            add("p.price < %s", maximum)
    if favorite_id is not None:
        add("EXISTS (SELECT 1 FROM favorites f WHERE f.product_id = p.id AND f.user_id = %s)", favorite_id)
    if product_id is not None:
        add("p.id = %s", product_id)

    where = " AND ".join(conditions) or "TRUE"
    order = """COALESCE((
        SELECT sum(oi.quantity) FROM order_items oi WHERE oi.product_id = p.id
    ), 0) DESC, p.id DESC LIMIT 6""" if popular else "p.name, p.id"
    with transaction() as cur:
        cur.execute(
            f"""SELECT {PRODUCT_FIELDS} FROM products p JOIN categories c ON c.id = p.category_id
                WHERE {where} ORDER BY {order}""",
            params,
        )
        return cur.fetchall()


def favorite_ids(user_id):
    with transaction() as cur:
        cur.execute("SELECT product_id FROM favorites WHERE user_id = %s", (user_id,))
        return {row["product_id"] for row in cur.fetchall()}


def save_favorite(user_id, product_id, checked):
    with transaction() as cur:
        if checked:
            cur.execute(
                "INSERT INTO favorites (user_id, product_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, product_id),
            )
        else:
            cur.execute("DELETE FROM favorites WHERE user_id = %s AND product_id = %s", (user_id, product_id))


def save_product(values, product_id=None):
    with transaction() as cur:
        if product_id is None:
            cur.execute(
                """INSERT INTO products (name, description, price, quantity, image_path, category_id,
                   players_min, players_max, play_time, age) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   RETURNING id""",
                values,
            )
        else:
            cur.execute(
                """UPDATE products SET name=%s, description=%s, price=%s, quantity=%s, image_path=%s,
                   category_id=%s, players_min=%s, players_max=%s, play_time=%s, age=%s WHERE id=%s
                   RETURNING id""",
                (*values, product_id),
            )
        row = cur.fetchone()
        return row["id"] if row else None


def delete_product(product_id):
    with transaction() as cur:
        cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
