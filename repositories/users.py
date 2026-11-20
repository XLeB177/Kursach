"""Запросы для учётных записей."""
from repositories.common import transaction
from services.validators import ValidationError

PUBLIC_FIELDS = "id, email, name, phone, avatar_path, role, status"


def create(email, password_hash, name, phone=None, role="client"):
    with transaction() as cur:
        cur.execute(
            f"""INSERT INTO users (email, password_hash, name, phone, role, status)
                VALUES (%s, %s, %s, %s, %s, 'active') RETURNING {PUBLIC_FIELDS}""",
            (email, password_hash, name, phone, role),
        )
        return cur.fetchone()


def find_by_email(email):
    with transaction() as cur:
        cur.execute(
            f"SELECT {PUBLIC_FIELDS}, password_hash FROM users WHERE lower(email) = %s",
            (email.lower(),),
        )
        return cur.fetchone()


def get(user_id):
    with transaction() as cur:
        cur.execute(f"SELECT {PUBLIC_FIELDS} FROM users WHERE id = %s", (user_id,))
        return cur.fetchone()


def update_profile(user_id, name, phone, avatar_path):
    with transaction() as cur:
        cur.execute(
            f"""UPDATE users SET name = %s, phone = %s, avatar_path = %s
                WHERE id = %s AND status = 'active' RETURNING {PUBLIC_FIELDS}""",
            (name, phone, avatar_path, user_id),
        )
        return cur.fetchone()


def list_users(role=None, search=""):
    with transaction() as cur:
        cur.execute(
            f"""SELECT {PUBLIC_FIELDS} FROM users
                WHERE (%s::text IS NULL OR role = %s)
                  AND (strpos(lower(name), lower(%s)) > 0
                       OR strpos(lower(email), lower(%s)) > 0)
                ORDER BY id""",
            (role, role, search, search),
        )
        return cur.fetchall()


def change(actor_id, user_id, *, remove=False, name=None, phone=None,
           role=None, status=None, password_hash=None):
    with transaction() as cur:
        # Последовательное изменение ролей и статусов защищает последнего админа.
        cur.execute("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE")
        cur.execute("SELECT role, status FROM users WHERE id = %s", (actor_id,))
        actor = cur.fetchone()
        if not actor or (actor["role"], actor["status"]) != ("admin", "active"):
            raise ValidationError("Недостаточно прав")
        cur.execute("SELECT role, status FROM users WHERE id = %s", (user_id,))
        current = cur.fetchone()
        if not current:
            raise ValidationError("Пользователь не найден")
        loses_access = remove or role != "admin" or status != "active"
        if user_id == actor_id and loses_access:
            raise ValidationError("Нельзя удалить, заблокировать или понизить самого себя")
        if current["role"] == "admin" and current["status"] == "active" and loses_access:
            cur.execute("SELECT count(*) AS n FROM users WHERE role = 'admin' AND status = 'active'")
            if cur.fetchone()["n"] == 1:
                raise ValidationError("В системе должен остаться активный администратор")
        if remove:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        else:
            cur.execute(
                """UPDATE users SET name = %s, phone = %s, role = %s, status = %s,
                   password_hash = COALESCE(%s, password_hash) WHERE id = %s""",
                (name, phone, role, status, password_hash, user_id),
            )
