"""Формы управления товарами, поставщиками и пользователями."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit

from services import auth, inventory
from services.permissions import ROLE_NAMES, STAFF
from ui.widgets.common import Form, actions, button, combo, line
from ui.widgets.files import choose_image, copy_image, discard_image

USER_STATUSES = {"active": "Активный", "blocked": "Заблокирован"}


class ProductForm(Form):
    def __init__(self, parent, actor_id, row):
        self.actor_id, self.row = actor_id, row or {}
        self.source = None
        super().__init__(parent, "Изменить товар" if row else "Добавить товар", self.save)
        self.fields = {}
        for key, title, default in (
            ("name", "Название", ""), ("price", "Цена, ₽", ""),
            ("quantity", "Количество", "0"), ("players_min", "Игроки от", "1"),
            ("players_max", "Игроки до", "4"), ("play_time", "Время игры, мин", "30"),
            ("age", "Возраст, лет", "6"),
        ):
            widget = line(self.row.get(key, default))
            self.fields[key] = widget
            self.form.addRow(title, widget)
        self.category = combo([(r["name"], r["id"]) for r in inventory.read_categories(actor_id, staff=True)],
                              self.row.get("category_id"))
        self.form.addRow("Категория", self.category)
        self.description = QPlainTextEdit(self.row.get("description", ""))
        self.description.setMaximumHeight(95)
        self.form.addRow("Описание", self.description)
        self.image = line(self.row.get("image_path", ""))
        self.image.setReadOnly(True)
        self.form.addRow("Изображение", actions(self.image, button("Выбрать", self.choose)))

    def choose(self):
        if path := choose_image(self):
            self.source = path
            self.image.setText(path)

    def save(self):
        fields = {key: widget.text() for key, widget in self.fields.items()}
        fields.update(category_id=self.category.currentData(), description=self.description.toPlainText())
        new = copy_image(self.source, "games") if self.source else None
        fields["image_path"] = new or self.row.get("image_path")
        try:
            inventory.save_product(self.actor_id, fields, self.row.get("id"))
        except Exception:
            discard_image(new)
            raise


class SupplierForm(Form):
    def __init__(self, parent, actor_id, row):
        self.actor_id, self.row = actor_id, row or {}
        super().__init__(parent, "Изменить поставщика" if row else "Добавить поставщика", self.save)
        self.name, self.email, self.phone = [line(self.row.get(key, "")) for key in ("name", "email", "phone")]
        self.status = combo([(n, n) for n in inventory.SUPPLIER_STATUSES], self.row.get("status"))
        for title, widget in zip(("Название", "Электронная почта", "Телефон", "Статус"),
                                 (self.name, self.email, self.phone, self.status)):
            self.form.addRow(title, widget)
        self.products = QListWidget()
        for product in inventory.list_products(actor_id):
            item = QListWidgetItem(product["name"], self.products)
            item.setData(Qt.ItemDataRole.UserRole, product["id"])
            checked = product["id"] in self.row.get("product_ids", [])
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.form.addRow("Поставляемые товары", self.products)

    def save(self):
        items = (self.products.item(i) for i in range(self.products.count()))
        selected = [item.data(Qt.ItemDataRole.UserRole) for item in items if item.checkState() == Qt.CheckState.Checked]
        inventory.save_supplier(
            self.actor_id, self.name.text(), self.email.text(), self.phone.text(),
            self.status.currentData(), selected, self.row.get("id"),
        )


class UserForm(Form):
    def __init__(self, parent, actor_id, row):
        self.actor_id, self.row = actor_id, row or {}
        super().__init__(parent, "Изменить пользователя" if row else "Добавить сотрудника", self.save)
        self.name, self.email, self.phone = [line(self.row.get(key, "")) for key in ("name", "email", "phone")]
        self.email.setReadOnly(bool(row))
        self.password = line(placeholder="Оставьте пустым для сохранения пароля" if row else "От 6 символов")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.role = combo([(name, key) for key, name in ROLE_NAMES.items() if row or key in STAFF], self.row.get("role"))
        self.status = combo([(name, key) for key, name in USER_STATUSES.items()], self.row.get("status", "active"))
        for title, widget in zip(
            ("Имя", "Электронная почта", "Телефон", "Пароль", "Роль", "Статус"),
            (self.name, self.email, self.phone, self.password, self.role, self.status),
        ):
            self.form.addRow(title, widget)
        self.status.setEnabled(bool(row))
        if self.row.get("id") == actor_id:
            self.role.setEnabled(False)
            self.status.setEnabled(False)

    def save(self):
        if self.row:
            auth.edit_user(
                self.actor_id, self.row["id"], self.name.text(), self.phone.text(),
                self.role.currentData(), self.status.currentData(), self.password.text(),
            )
        else:
            auth.create_staff(
                self.actor_id, self.email.text(), self.password.text(), self.name.text(),
                self.phone.text(), self.role.currentData(),
            )
