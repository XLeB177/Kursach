"""Витрина магазина, карточки и корзина клиента."""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QMessageBox, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from services import inventory, order_flow
from services.calculations import totals
from ui.widgets.common import (
    actions, attempt, button, combo, confirm, fill, guarded, label, line, money, table,
)
from ui.widgets.images import product_pixmap

TIMES = [("До 30 мин", (0, 30)), ("31–60 мин", (30, 60)),
         ("61–120 мин", (60, 120)), ("Более 120 мин", (120, None))]


class CatalogPage(QWidget):
    def __init__(self, parent, actor_id, mode, navigate):
        super().__init__(parent)
        self.actor_id = actor_id
        self.mode = mode
        self.outer = QVBoxLayout(self)
        self.outer.setSpacing(14)
        self.search = line(placeholder="Поиск по названию или описанию")
        self.category = self.players = self.duration = self.age = None
        if mode == "Главная":
            banner = QFrame()
            banner.setObjectName("banner")
            content = QVBoxLayout(banner)
            content.setContentsMargins(24, 20, 24, 20)
            content.addWidget(label("Настольные игры для всей семьи", "heading"))
            content.addWidget(button("Перейти в каталог", lambda: navigate("Каталог"), True),
                              alignment=Qt.AlignmentFlag.AlignLeft)
            self.outer.addWidget(banner)
            self.outer.addWidget(label("Популярные игры", "subheading"))
        else:
            self.outer.addWidget(self.search)
        self.timer = QTimer(self, interval=260, singleShot=True)
        self.timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda: self.timer.start())
        if mode == "Каталог":
            self.add_filters()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.outer.addWidget(self.scroll, 1)
        self.refresh()

    def add_filters(self):
        group = QHBoxLayout()
        self.players = combo([("Все", None)] + [(str(n), n) for n in range(1, 6)] + [("6 и более", 6)])
        self.duration = combo([("Все", None)] + TIMES)
        self.age = combo([("Все", None)] + [(f"{n}+", n) for n in (3, 6, 8, 10, 12, 14, 16)])
        for title, widget in (
            ("Количество игроков", self.players), ("Время игры", self.duration), ("Возраст", self.age),
        ):
            group.addWidget(label(title))
            group.addWidget(widget, 1)
            widget.currentIndexChanged.connect(lambda: self.refresh())
        self.outer.addLayout(group)

        category_row = QGridLayout()
        choices = [{"name": "Все", "id": None}, *inventory.read_categories(self.actor_id)]
        self.category_buttons = []
        for index, category in enumerate(choices):
            control = button(category["name"], lambda item=category: self.select_category(item["id"]))
            control.setCheckable(True)
            control.setChecked(index == 0)
            self.category_buttons.append((category["id"], control))
            category_row.addWidget(control, index // 4, index % 4)
        self.outer.addWidget(label("Категории"))
        self.outer.addLayout(category_row)

    def select_category(self, category_id):
        self.category = category_id
        for key, control in self.category_buttons:
            control.setChecked(key == category_id)
        self.refresh()

    @guarded
    def refresh(self):
        filters = {"search": self.search.text(), "popular": self.mode == "Главная"}
        if self.players:
            filters.update(category=self.category, players=self.players.currentData(),
                           play_time=self.duration.currentData(), age=self.age.currentData())
        games = inventory.browse(self.actor_id, favorite=self.mode == "Избранное", **filters)
        favorites = inventory.favorite_ids(self.actor_id)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        grid.setSpacing(12)
        for column in range(3):
            grid.setColumnStretch(column, 1)
        if not games:
            grid.addWidget(label("В избранном пока нет подходящих игр" if self.mode == "Избранное"
                                 else "Игры не найдены"), 0, 0, 1, 3)
        for index, game in enumerate(games):
            grid.addWidget(self.card(game, game["id"] in favorites), index // 3, index % 3)
        self.scroll.setWidget(body)

    def card(self, game, favorite):
        card = QFrame()
        card.setObjectName("gameCard")
        content = QVBoxLayout(card)
        content.setContentsMargins(13, 13, 13, 13)
        photo = label("")
        photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo.setPixmap(product_pixmap(game["image_path"], 125))
        title = label(game["name"], "subheading")
        title.setWordWrap(True)
        content.addWidget(photo)
        content.addWidget(title)
        content.addWidget(label(f"{money(game['price'])}  ·  " +
                                (f"{game['quantity']} шт." if game["quantity"] else "Нет в наличии")))
        content.addWidget(button("Открыть карточку", lambda: self.open_game(game["id"]), True))
        content.addWidget(button(
            "Убрать из избранного" if favorite else "Добавить в избранное",
            lambda: self.toggle_favorite(game["id"], not favorite),
        ))
        return card

    @guarded
    def toggle_favorite(self, product_id, checked):
        inventory.toggle_favorite(self.actor_id, product_id, checked)
        self.refresh()

    @guarded
    def open_game(self, product_id):
        games = inventory.browse(self.actor_id, product_id=product_id)
        if not games:
            QMessageBox.information(self, "Карточка товара", "Товар больше недоступен")
            self.refresh()
            return
        game = games[0]
        dialog = QDialog(self)
        dialog.setWindowTitle(game["name"])
        dialog.setMinimumWidth(480)
        layout = QVBoxLayout(dialog)
        photo = label("")
        photo.setPixmap(product_pixmap(game["image_path"], 190))
        layout.addWidget(photo, alignment=Qt.AlignmentFlag.AlignHCenter)
        title = label(game["name"], "heading")
        title.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(label(money(game["price"]), "subheading"))
        layout.addWidget(label(f"{game['players_min']}–{game['players_max']} игроков  ·  "
                               f"{game['play_time']} мин  ·  {game['age']}+"))
        layout.addWidget(label("Описание", "subheading"))
        description = label(game["description"])
        description.setWordWrap(True)
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(description)
        scroll.setMinimumHeight(85)
        layout.addWidget(scroll)
        if game["quantity"]:
            amount = QSpinBox()
            amount.setRange(1, game["quantity"])
            layout.addWidget(actions(
                button("−", amount.stepDown), amount, button("+", amount.stepUp),
                button("Добавить в корзину", lambda: self.add_to_cart(dialog, game["id"], amount.value()), True),
            ))
        else:
            layout.addWidget(label("Нет в наличии"))
        favorites = inventory.favorite_ids(self.actor_id)
        toggle = button("Убрать из избранного" if product_id in favorites else "Добавить в избранное",
                        lambda: self.update_detail_favorite(dialog, toggle, product_id))
        toggle.setProperty("favorited", product_id in favorites)
        layout.addWidget(toggle)
        dialog.exec()

    def update_detail_favorite(self, dialog, control, product_id):
        checked = not control.property("favorited")
        if attempt(dialog, inventory.toggle_favorite, self.actor_id, product_id, checked)[0]:
            control.setProperty("favorited", checked)
            control.setText("Убрать из избранного" if checked else "Добавить в избранное")
            self.refresh()

    def add_to_cart(self, dialog, product_id, quantity):
        if attempt(dialog, order_flow.change_cart, self.actor_id, product_id, quantity, add=True)[0]:
            QMessageBox.information(dialog, "Корзина", "Игра добавлена в корзину")


class CartPage(QWidget):
    def __init__(self, parent, actor_id):
        super().__init__(parent)
        self.actor_id = actor_id
        layout = QVBoxLayout(self)
        self.table = table(("Фото", "Название", "Цена", "Количество", "Действия"), stretch=1)
        layout.addWidget(self.table, 1)
        self.total = label("", "subheading")
        self.order = button("Заказать", self.checkout, True)
        self.clear = button("Очистить корзину", self.clear_cart)
        layout.addWidget(self.total)
        layout.addWidget(actions(self.clear, self.order))
        self.refresh()

    @guarded
    def refresh(self):
        games = order_flow.get_cart(self.actor_id)
        rows = []
        for game in games:
            photo = label("")
            photo.setPixmap(product_pixmap(game["image_path"], 48))
            name = game["name"]
            if game["stock"] < game["quantity"]:
                name += f" (доступно {game['stock']} шт.)"
            amount = QSpinBox()
            amount.setRange(1, max(game["stock"], game["quantity"]))
            amount.setValue(game["quantity"])
            rows.append((photo, name, money(game["price"]), amount, actions(
                button("Сохранить", lambda key=game["id"], field=amount: self.change(key, field.value())),
                button("Удалить", lambda key=game["id"]: self.remove(key)),
            )))
        fill(self.table, rows)
        for row in range(len(rows)):
            self.table.setRowHeight(row, 54)
        count, total = totals(games)
        self.total.setText(f"Итого · {count} шт. · {money(total)}")
        self.order.setEnabled(bool(games))
        self.clear.setEnabled(bool(games))

    @guarded
    def change(self, product_id, quantity):
        order_flow.change_cart(self.actor_id, product_id, quantity)
        self.refresh()

    def remove(self, product_id):
        if confirm(self, "Удалить игру из корзины?"):
            self.change(product_id, 0)

    @guarded
    def clear_cart(self):
        if confirm(self, "Очистить корзину?"):
            order_flow.clear_cart(self.actor_id)
            self.refresh()

    @guarded
    def checkout(self):
        order_id = order_flow.checkout(self.actor_id)
        self.refresh()
        QMessageBox.information(self, "Заказ оформлен", f"Заказ № {order_id} оформлен. Получение в магазине.")
