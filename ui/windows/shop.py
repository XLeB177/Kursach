"""Основное окно магазина и навигация по ролям."""
from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from repositories import users
from services.permissions import ROLE_NAMES, allowed, require
from services.validators import ValidationError
from ui.widgets.common import attempt, button, label
from ui.widgets.images import avatar_pixmap, set_logo_on_label
from ui.windows.auth import AuthWindow
from ui.windows.client import CartPage, CatalogPage
from ui.windows.orders import OrdersPage
from ui.windows.profile import ProfilePage
from ui.windows.staff import StaffPage

STYLES = Path(__file__).resolve().parents[1] / "styles"
NAVIGATION = (
    ("Главная", "catalog"), ("Каталог", "catalog"), ("Корзина", "cart"), ("Избранное", "favorites"),
    ("Товары", "products"), ("Заказы", "orders"), ("Пользователи", "view_users"),
    ("Поставщики", "suppliers"),
)


class ShopWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("BoardGamesShop", "Desktop")
        self.user = None
        self.theme = "light"
        self.setWindowTitle("Магазин настольных игр")
        self.resize(1180, 780)
        self.setMinimumSize(875, 650)
        self.logout()

    def apply_theme(self, theme):
        self.theme = theme if theme in ("light", "dark") else "light"
        colors = (STYLES / f"{self.theme}.qss").read_text(encoding="utf-8")
        common = (STYLES / "common.qss").read_text(encoding="utf-8")
        self.setStyleSheet(common + "\n" + colors)
        if self.user:
            self.settings.setValue(f"users/{self.user['id']}/theme", self.theme)

    def logout(self):
        self.user = None
        self.apply_theme("dark")
        self.setCentralWidget(AuthWindow(self.logged_in))

    def logged_in(self, user):
        self.user = user
        self.apply_theme(self.settings.value(f"users/{user['id']}/theme", "light"))
        container = QWidget()
        outer = QHBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(212)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(14, 18, 14, 16)
        nav.setSpacing(8)
        logo = label("", "brand")
        logo.setWordWrap(True)
        set_logo_on_label(logo)
        nav.addWidget(logo)
        self.profile = button("", lambda: self.open_section("Профиль"))
        self.profile.setCheckable(True)
        nav.addWidget(self.profile)
        self.role = label("")
        nav.addWidget(self.role)
        self.update_profile(user)
        nav.addSpacing(16)
        self.links = {"Профиль": self.profile}
        for section, right in NAVIGATION:
            if allowed(user["role"], right):
                link = button(section, lambda name=section: self.open_section(name))
                link.setCheckable(True)
                nav.addWidget(link)
                self.links[section] = link
        nav.addStretch()
        nav.addWidget(button("Выйти", self.logout))
        outer.addWidget(sidebar)
        body = QWidget()
        self.page_layout = QVBoxLayout(body)
        self.page_layout.setContentsMargins(18, 18, 18, 12)
        self.section_title = label("", "heading")
        self.page_layout.addWidget(self.section_title)
        self.page = None
        self.section = None
        outer.addWidget(body, 1)
        self.setCentralWidget(container)
        self.open_section("Главная" if user["role"] == "client" else "Товары")

    def update_profile(self, user):
        self.user = user
        self.profile.setText(user["name"])
        self.profile.setIcon(QIcon(avatar_pixmap(user["avatar_path"], user["name"], 28)))
        self.role.setText(ROLE_NAMES[user["role"]])

    def open_section(self, section):
        if self.user is None:
            return
        if not attempt(self, self.switch_section, section)[0]:
            for name, link in self.links.items():
                link.setChecked(name == self.section)

    def switch_section(self, section):
        actor = users.get(self.user["id"])
        if not actor or actor["status"] != "active" or actor["role"] != self.user["role"]:
            self.logout()
            raise ValidationError("Права учётной записи изменились. Войдите снова")
        actor_id = actor["id"]
        right = "profile" if section == "Профиль" else dict(NAVIGATION)[section]
        require(actor_id, right)
        if section == "Профиль":
            page = ProfilePage(self, actor, self.theme, self.apply_theme, self.update_profile)
        elif section in ("Главная", "Каталог", "Избранное"):
            page = CatalogPage(self, actor_id, section, self.open_section)
        elif section == "Корзина":
            page = CartPage(self, actor_id)
        elif section == "Заказы":
            page = OrdersPage(self, actor_id)
        else:
            page = StaffPage(self, actor_id, section)
        if self.page is not None:
            self.page.hide()
            self.page_layout.removeWidget(self.page)
            self.page.deleteLater()
        self.page = page
        self.section = section
        self.section_title.setText(section)
        self.page_layout.addWidget(page, 1)
        for name, link in self.links.items():
            link.setChecked(name == section)
