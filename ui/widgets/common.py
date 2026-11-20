"""Общие поля, таблицы и обработка ошибок интерфейса."""
import logging
from functools import wraps

from psycopg2 import Error as DatabaseError
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from services.validators import ValidationError

logger = logging.getLogger(__name__)


def attempt(parent, operation, *args, **kwargs):
    try:
        return True, operation(*args, **kwargs)
    except DatabaseError as exc:
        logger.warning("Ошибка PostgreSQL (%s)", exc.pgcode or type(exc).__name__)
        message = "Не удалось выполнить операцию с базой данных. Проверьте подключение и повторите попытку."
    except ValidationError as exc:
        message = str(exc)
    except ValueError as exc:
        message = str(exc)
    except OSError:
        message = "Не удалось прочитать или сохранить файл"
    QMessageBox.warning(parent, "Не удалось выполнить действие", message)
    return False, None


def guarded(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        return attempt(self, fn, self, *args, **kwargs)[1]
    return wrapper


def button(text, callback, primary=False):
    control = QPushButton(text)
    if primary:
        control.setProperty("primary", True)
    control.clicked.connect(lambda: callback())
    return control


def label(text, name=None):
    control = QLabel()
    control.setTextFormat(Qt.TextFormat.PlainText)
    control.setText(str(text))
    if name:
        control.setObjectName(name)
    return control


def line(value="", placeholder=""):
    widget = QLineEdit(str(value) if value is not None else "")
    widget.setPlaceholderText(placeholder)
    return widget


def combo(choices, current=None):
    widget = QComboBox()
    for text, value in choices:
        widget.addItem(text, value)
    index = widget.findData(current)
    if index >= 0:
        widget.setCurrentIndex(index)
    return widget


def money(amount):
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",") + " ₽"


def date(value):
    return value.strftime("%d.%m.%Y %H:%M")


def confirm(parent, text):
    return QMessageBox.question(parent, "Подтверждение", text) == QMessageBox.StandardButton.Yes


def table(headers, stretch=None):
    widget = QTableWidget(0, len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    widget.setAlternatingRowColors(True)
    widget.setWordWrap(True)
    widget.verticalHeader().hide()
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch is None:
        widget.horizontalHeader().setStretchLastSection(True)
    else:
        widget.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
    return widget


def fill(widget, rows):
    widget.setRowCount(0)
    for row, values in enumerate(rows):
        widget.insertRow(row)
        for column, value in enumerate(values):
            if isinstance(value, QWidget):
                widget.setCellWidget(row, column, value)
            else:
                item = QTableWidgetItem(str(value) if value is not None else "—")
                widget.setItem(row, column, item)
    widget.resizeRowsToContents()


def actions(*buttons):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(4, 3, 4, 3)
    for control in buttons:
        layout.addWidget(control)
    return widget


class Form(QDialog):
    def __init__(self, parent, title, save):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.outer = QVBoxLayout(self)
        self.form = QFormLayout()
        self.outer.addLayout(self.form)
        self.controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                         QDialogButtonBox.StandardButton.Cancel)
        self.controls.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        self.controls.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        self.outer.addWidget(self.controls)
        self.controls.accepted.connect(lambda: self.submit(save))
        self.controls.rejected.connect(self.reject)

    def submit(self, save):
        if attempt(self, save)[0]:
            self.accept()
