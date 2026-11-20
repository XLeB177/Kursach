"""Личный профиль, тема и история заказов."""
from pathlib import Path

from PyQt6.QtWidgets import QDialog, QFormLayout, QMessageBox, QVBoxLayout, QWidget

from services import auth
from services.permissions import RIGHTS, ROLE_NAMES, allowed
from ui.widgets.common import actions, button, combo, guarded, label, line
from ui.widgets.files import choose_image, copy_image, discard_image
from ui.widgets.images import avatar_pixmap
from ui.windows.orders import OrdersPage


class ProfilePage(QWidget):
    def __init__(self, parent, user, theme, set_theme, on_update):
        super().__init__(parent)
        self.user = user
        self.on_update = on_update
        self.source = None
        outer = QVBoxLayout(self)
        form = QFormLayout()
        outer.addLayout(form)
        self.name = line(user["name"])
        self.phone = line(user["phone"])
        email = line(user["email"])
        email.setReadOnly(True)
        self.avatar = label("")
        self.avatar.setPixmap(avatar_pixmap(user["avatar_path"], user["name"], 76))
        self.file_name = label("")
        form.addRow("Аватар", actions(self.avatar, button("Изменить аватар", self.choose), self.file_name))
        form.addRow("Имя", self.name)
        form.addRow("Телефон", self.phone)
        form.addRow("Электронная почта", email)
        style = combo([("Светлая", "light"), ("Тёмная", "dark")], theme)
        style.currentIndexChanged.connect(lambda: set_theme(style.currentData()))
        form.addRow("Тема", style)
        outer.addWidget(button("Сохранить профиль", self.save, True))
        if user["role"] == "client":
            outer.addWidget(button("Мои заказы", self.orders))
        else:
            outer.addWidget(label("Роль и права доступа", "subheading"))
            outer.addWidget(label(ROLE_NAMES[user["role"]]))
            for action, (description, _) in RIGHTS.items():
                if allowed(user["role"], action):
                    outer.addWidget(label(f"•  {description}"))
        outer.addStretch()

    def choose(self):
        if path := choose_image(self):
            self.source = path
            self.file_name.setText(Path(path).name)

    @guarded
    def save(self):
        new_path = copy_image(self.source, "avatars", limit=2 * 1024 * 1024) if self.source else None
        try:
            profile = auth.save_profile(
                self.user["id"], self.name.text(), self.phone.text(), new_path or self.user["avatar_path"],
            )
        except Exception:
            discard_image(new_path)
            raise
        previous = self.user["avatar_path"]
        self.user = profile
        if new_path and previous:
            old_path = Path(previous)
            if old_path.parent.as_posix() == "assets/avatars" and old_path.name != ".gitkeep":
                discard_image(previous)
        self.source = None
        self.file_name.clear()
        self.avatar.setPixmap(avatar_pixmap(profile["avatar_path"], profile["name"], 76))
        self.name.setText(profile["name"])
        self.phone.setText(profile["phone"] or "")
        self.on_update(profile)
        QMessageBox.information(self, "Профиль", "Изменения сохранены")

    def orders(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ваши заказы")
        dialog.resize(930, 475)
        layout = QVBoxLayout(dialog)
        layout.addWidget(OrdersPage(dialog, self.user["id"], own=True))
        dialog.exec()
