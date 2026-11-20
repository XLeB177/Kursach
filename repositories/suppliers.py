"""Запросы поставщиков и их ассортимента."""
from repositories.common import transaction
from services.validators import ValidationError


def list_suppliers(search="", status=None):
    with transaction() as cur:
        cur.execute(
            """SELECT s.id, s.name, s.email, s.phone, s.status,
                      COALESCE(array_agg(p.id ORDER BY p.name) FILTER (WHERE p.id IS NOT NULL),
                               ARRAY[]::integer[]) AS product_ids,
                      COALESCE(string_agg(p.name, ', ' ORDER BY p.name), '') AS products
               FROM suppliers s LEFT JOIN supplier_products sp ON sp.supplier_id = s.id
               LEFT JOIN products p ON p.id = sp.product_id
               WHERE strpos(lower(s.name), lower(%s)) > 0 AND (%s::text IS NULL OR s.status = %s)
               GROUP BY s.id ORDER BY s.name""",
            (search, status, status),
        )
        return cur.fetchall()


def save(values, product_ids, supplier_id=None):
    with transaction() as cur:
        if supplier_id is None:
            cur.execute(
                "INSERT INTO suppliers (name, email, phone, status) VALUES (%s,%s,%s,%s) RETURNING id",
                values,
            )
        else:
            cur.execute(
                "UPDATE suppliers SET name=%s, email=%s, phone=%s, status=%s WHERE id=%s RETURNING id",
                (*values, supplier_id),
            )
        row = cur.fetchone()
        if not row:
            raise ValidationError("Поставщик не найден")
        supplier_id = row["id"]
        cur.execute("DELETE FROM supplier_products WHERE supplier_id=%s", (supplier_id,))
        cur.executemany(
            "INSERT INTO supplier_products (supplier_id, product_id) VALUES (%s,%s)",
            [(supplier_id, product_id) for product_id in set(product_ids)],
        )


def delete(supplier_id):
    with transaction() as cur:
        cur.execute("DELETE FROM suppliers WHERE id = %s", (supplier_id,))
