"""Список заказов клиента и рабочий раздел сотрудников."""
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QSpinBox, QTabBar, QVBoxLayout, QWidget

from repositories.orders import NEW, STATUSES
from services import inventory, order_flow
from services.validators import ValidationError
from ui.widgets.common import (
    Form, actions, button, combo, confirm, date, fill, guarded, label, line, money, table,
)
from ui.widgets.files import download_receipt


class OrdersPage(QWidget):
    def __init__(self, parent, actor_id, own=False):
        super().__init__(parent)
        self.actor_id, self.own = actor_id, own
        outer = QVBoxLayout(self)
        self.search = self.sort = self.tabs = None
        if not own:
            self.tabs = QTabBar()
            for title in ("Все", "Новые", "В обработке", "Доставленные"):
                self.tabs.addTab(title)
            outer.addWidget(self.tabs)
            self.search = line(placeholder="ID, имя клиента, почта или название товара")
            self.sort = combo([("Сначала новые", True), ("Сначала старые", False)])
            controls = QHBoxLayout()
            controls.addWidget(self.search, 1)
            controls.addWidget(self.sort)
            controls.addWidget(button("Добавить заказ", self.edit, True))
            outer.addLayout(controls)
        headers = ("ID",) if own else ("ID", "Пользователь")
        self.table = table(headers + ("Содержимое", "Сумма", "Статус", "Дата заказа", "Чек", "Действия"), stretch=len(headers))
        outer.addWidget(self.table, 1)
        self.message = label("")
        outer.addWidget(self.message)
        if not own:
            self.timer = QTimer(self, interval=260, singleShot=True)
            self.timer.timeout.connect(self.refresh)
            self.search.textChanged.connect(lambda: self.timer.start())
            self.tabs.currentChanged.connect(lambda: self.refresh())
            self.sort.currentIndexChanged.connect(lambda: self.refresh())
        self.refresh()

    @guarded
    def refresh(self):
        filters = {} if self.own else {
            "search": self.search.text().strip(),
            "status": (None, *STATUSES)[self.tabs.currentIndex()],
            "newest": self.sort.currentData(),
        }
        rows = []
        for order in order_flow.list_orders(self.actor_id, own=self.own, **filters):
            key = order["id"]
            summary = (key,) if self.own else (key, f"{order['name']}\n{order['email']}")
            receipt = button("Скачать чек", lambda order_id=key: self.receipt(order_id))
            remove = button("Удалить", lambda order_id=key: self.delete(order_id))
            remove.setEnabled(not self.own or order["status"] == NEW)
            operations = [remove]
            if not self.own:
                operations.insert(0, button("Изменить", lambda order_id=key: self.edit(order_id)))
            rows.append((*summary, order["content"], money(order["total"]), order["status"],
                         date(order["created_at"]), receipt, actions(*operations)))
        fill(self.table, rows)
        for index in range(len(rows)):
            self.table.setRowHeight(index, max(48, self.table.rowHeight(index)))
        self.message.setText("" if rows else "Заказы не найдены")

    @guarded
    def receipt(self, order_id):
        download_receipt(self, self.actor_id, order_id)

    @guarded
    def delete(self, order_id):
        if confirm(self, f"Удалить заказ № {order_id}?"):
            order_flow.delete(self.actor_id, order_id, own=self.own)
            self.refresh()

    @guarded
    def edit(self, order_id=None):
        if OrderForm(self, self.actor_id, order_id).exec() == QDialog.DialogCode.Accepted:
            self.refresh()


class OrderForm(Form):
    def __init__(self, parent, actor_id, order_id):
        self.actor_id = actor_id
        self.order_id = order_id
        order, existing = order_flow.detail(actor_id, order_id) if order_id else (None, [])
        self.editable = not order or order["status"] == NEW
        super().__init__(parent, "Изменить заказ" if order else "Добавить заказ", self.save)
        buyer_choices = ([(f"{order['name']} ({order['email']})", order["user_id"])] if order else
                         [(f"{row['name']} ({row['email']})", row["id"]) for row in order_flow.clients(actor_id)])
        self.client = combo(buyer_choices)
        self.client.setEnabled(order is None)
        self.form.addRow("Пользователь", self.client)
        current = order["status"] if order else NEW
        index = STATUSES.index(current)
        self.status = combo([(status, status) for status in STATUSES[index:index + (2 if order else 1)]])
        self.form.addRow("Статус", self.status)
        self.positions = table(("Товар", "Количество", ""), stretch=0)
        self.positions.setMinimumHeight(220)
        self.outer.insertWidget(1, self.positions)
        self.product_choices = [(f"{row['name']} · {row['quantity']} шт.", row["id"])
                                for row in inventory.list_products(actor_id)] if self.editable else []
        if self.editable:
            self.outer.insertWidget(2, button("Добавить позицию", lambda: self.add_line()))
        for row in existing:
            self.add_line(row["product_id"], row["quantity"], row["name"])
        if not order:
            self.add_line()

    def add_line(self, product_id=None, quantity=1, name=None):
        index = self.positions.rowCount()
        self.positions.insertRow(index)
        product = combo(self.product_choices if self.editable else [(name, product_id)], product_id)
        amount = QSpinBox()
        amount.setRange(1, 1_000_000)
        amount.setValue(quantity)
        remove = QPushButton("Убрать")
        product.setEnabled(self.editable)
        amount.setEnabled(self.editable)
        remove.setVisible(self.editable)
        remove.clicked.connect(lambda: self.remove_line(remove))
        for column, widget in enumerate((product, amount, remove)):
            self.positions.setCellWidget(index, column, widget)
        self.positions.setRowHeight(index, 36)

    def remove_line(self, control):
        for index in range(self.positions.rowCount()):
            if self.positions.cellWidget(index, 2) is control:
                self.positions.removeRow(index)
                return

    def save(self):
        items = None
        if self.editable:
            items = [(self.positions.cellWidget(i, 0).currentData(), self.positions.cellWidget(i, 1).value())
                     for i in range(self.positions.rowCount())]
            if any(product is None for product, _ in items):
                raise ValidationError("Выберите товар для каждой позиции")
        if self.order_id is None:
            if self.client.currentData() is None:
                raise ValidationError("Выберите пользователя")
            order_flow.create(self.actor_id, self.client.currentData(), items)
        else:
            order_flow.edit(self.actor_id, self.order_id, self.status.currentData(), items)
