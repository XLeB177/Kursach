"""Управление товарами, поставщиками и пользователями."""
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QWidget

from services import auth, inventory
from services.permissions import ROLE_NAMES
from ui.widgets.common import actions, button, combo, confirm, fill, guarded, label, line, money, table
from ui.widgets.images import avatar_pixmap, product_pixmap
from ui.windows.staff_forms import ProductForm, SupplierForm, UserForm, USER_STATUSES

SECTIONS = {
    "Товары": (("ID", "Фото", "Название", "Категория", "Цена", "Количество", "Действия"),
               ProductForm, "Добавить товар"),
    "Поставщики": (("ID", "Название", "Почта", "Телефон", "Поставляемые товары", "Статус", "Действия"),
                   SupplierForm, "Добавить поставщика"),
    "Пользователи": (("ID", "Имя", "Почта", "Телефон", "Аватар", "Роль", "Статус", "Действия"),
                    UserForm, "Добавить пользователя"),
}


class StaffPage(QWidget):
    def __init__(self, parent, actor_id, section):
        super().__init__(parent)
        self.actor_id, self.section = actor_id, section
        headers, self.form, add_label = SECTIONS[section]
        outer = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.search = line(placeholder="Поиск по имени или почте" if section == "Пользователи" else "Поиск по названию")
        controls.addWidget(self.search, 1)
        self.first = self.second = None
        if section == "Товары":
            self.first = combo([("Все категории", None)] + [
                (row["name"], row["id"]) for row in inventory.read_categories(actor_id, staff=True)
            ])
            self.second = combo([("Любая цена", None), ("До 1 000 ₽", (0, 1000)),
                                 ("1 000–2 000 ₽", (1000, 2000)), ("2 000–3 000 ₽", (2000, 3000)),
                                 ("От 3 000 ₽", (3000, None))])
        elif section == "Поставщики":
            self.first = combo([("Все статусы", None)] + [(s, s) for s in inventory.SUPPLIER_STATUSES])
        else:
            self.first = combo([("Все роли", None)] + [(name, key) for key, name in ROLE_NAMES.items()])
            self.second = combo([("Все статусы", None)] + [(name, key) for key, name in USER_STATUSES.items()])
        for control in (self.first, self.second):
            if control:
                controls.addWidget(control)
                control.currentIndexChanged.connect(lambda: self.refresh())
        controls.addWidget(button(add_label, self.edit, True))
        outer.addLayout(controls)
        self.table = table(headers, stretch={"Товары": 2, "Поставщики": 4, "Пользователи": 2}[section])
        outer.addWidget(self.table, 1)
        self.message = label("")
        outer.addWidget(self.message)
        self.timer = QTimer(self, interval=260, singleShot=True)
        self.timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda: self.timer.start())
        self.refresh()

    @guarded
    def refresh(self):
        rows = []
        search = self.search.text().strip()
        selection = self.first.currentData()
        if self.section == "Товары":
            for row in inventory.list_products(self.actor_id, search=search, category=selection,
                                               price=self.second.currentData()):
                photo = label("")
                photo.setPixmap(product_pixmap(row["image_path"], 46))
                rows.append((row["id"], photo, row["name"], row["category"], money(row["price"]),
                             row["quantity"] or "Нет в наличии", self.row_actions(row)))
        elif self.section == "Поставщики":
            for row in inventory.list_suppliers(self.actor_id, search, selection):
                rows.append((row["id"], row["name"], row["email"], row["phone"], row["products"],
                             row["status"], self.row_actions(row)))
        else:
            status = self.second.currentData()
            for row in auth.list_users(self.actor_id, selection, search):
                if status and row["status"] != status:
                    continue
                avatar = label("")
                avatar.setPixmap(avatar_pixmap(row["avatar_path"], row["name"], 42))
                rows.append((row["id"], row["name"], row["email"], row["phone"], avatar,
                             ROLE_NAMES[row["role"]], USER_STATUSES[row["status"]], self.row_actions(row)))
        fill(self.table, rows)
        for index in range(len(rows)):
            self.table.setRowHeight(index, max(52, self.table.rowHeight(index)))
        self.message.setText("" if rows else "Записи не найдены")

    def row_actions(self, row):
        remove = button("Удалить", lambda: self.delete(row))
        remove.setEnabled(self.section != "Пользователи" or row["id"] != self.actor_id)
        return actions(button("Изменить", lambda: self.edit(row)), remove)

    @guarded
    def edit(self, row=None):
        if self.form(self, self.actor_id, row).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    @guarded
    def delete(self, row):
        if confirm(self, f"Удалить запись «{row['name']}»?"):
            operations = {"Товары": inventory.delete_product, "Поставщики": inventory.delete_supplier,
                          "Пользователи": auth.delete_user}
            operations[self.section](self.actor_id, row["id"])
            self.refresh()
