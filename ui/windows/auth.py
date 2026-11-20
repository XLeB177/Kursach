"""Окна входа и регистрации."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QFrame, QLineEdit, QStackedWidget, QVBoxLayout, QWidget

from services import auth
from ui.widgets.common import button, guarded, label, line
from ui.widgets.images import set_logo_on_label


class AuthWindow(QStackedWidget):
    def __init__(self, on_login):
        super().__init__()
        self.on_login = on_login
        self.addWidget(self.page(False))
        self.addWidget(self.page(True))

    def page(self, registration):
        page = QWidget()
        page.setObjectName("authPage")
        outer = QVBoxLayout(page)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel = QFrame()
        panel.setObjectName("authPanel")
        panel.setFixedWidth(410)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(32, 30, 32, 30)
        layout.setSpacing(12)
        logo = label("", "brand")
        set_logo_on_label(logo)
        logo.setWordWrap(True)
        logo.setScaledContents(False)
        layout.addWidget(logo)
        layout.addWidget(label("Регистрация" if registration else "Вход", "heading"))
        email = line(placeholder="Электронная почта")
        password = line(placeholder="Пароль")
        password.setEchoMode(QLineEdit.EchoMode.Password)
        for field in (email, password):
            field.setAccessibleName(field.placeholderText())
            layout.addWidget(field)
        if registration:
            confirmation = line(placeholder="Подтверждение пароля")
            confirmation.setAccessibleName(confirmation.placeholderText())
            confirmation.setEchoMode(QLineEdit.EchoMode.Password)
            consent = QCheckBox("Согласие на обработку персональных данных")
            layout.addWidget(confirmation)
            layout.addWidget(consent)

            def submit():
                self.register(email, password, confirmation, consent)
        else:
            self.email = email

            def submit():
                self.login(email, password)

        password.returnPressed.connect(submit)
        layout.addWidget(button("Зарегистрироваться" if registration else "Войти", submit, True))
        layout.addWidget(button(
            "Уже есть аккаунт? Войти" if registration else "Нет аккаунта? Зарегистрироваться",
            lambda: self.setCurrentIndex(0 if registration else 1),
        ))
        outer.addWidget(panel)
        return page

    @guarded
    def login(self, email, password):
        user = auth.login(email.text(), password.text())
        password.clear()
        self.on_login(user)

    @guarded
    def register(self, email, password, confirmation, consent):
        user = auth.register(email.text(), password.text(), confirmation.text(), consent.isChecked())
        self.email.setText(user["email"])
        for field in (email, password, confirmation):
            field.clear()
        consent.setChecked(False)
        self.setCurrentIndex(0)
