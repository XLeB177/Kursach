"""Загрузка картинок: нет файла — заглушка, без ошибки."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel

_ROOT = Path(__file__).resolve().parent.parent.parent
LOGO_RELATIVE = "assets/logo.png"


def load_pixmap(relative_path: str | None) -> QPixmap | None:
    """Вернуть картинку или None, если пути нет или файл не читается."""
    if not relative_path:
        return None
    path = _ROOT / relative_path
    try:
        if not path.is_file():
            return None
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return None
        return pixmap
    except OSError:
        return None


def logo_pixmap() -> QPixmap | None:
    """Логотип или None — тогда в окне текст «Магазин настольных игр»."""
    return load_pixmap(LOGO_RELATIVE)


def set_logo_on_label(label: QLabel) -> None:
    """Показать логотип или текст, если файла нет."""
    pixmap = logo_pixmap()
    if pixmap is None:
        label.clear()
        label.setText("Магазин настольных игр")
        return
    label.setText("")
    label.setPixmap(pixmap)


def product_placeholder(size: int = 160) -> QPixmap:
    """Серый квадрат «Нет фото»."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#B0B0B0"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#333333"))
    painter.setFont(QFont("Segoe UI", max(10, size // 12)))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Нет фото")
    painter.end()
    return pixmap


def avatar_placeholder(name: str, size: int = 64) -> QPixmap:
    """Круг с первой буквой имени."""
    letter = (name or "?").strip()[:1].upper() or "?"
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#5A6A7A"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, size - 1, size - 1)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", max(10, size // 2), QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()
    return pixmap


def product_pixmap(relative_path: str | None, size: int = 160) -> QPixmap:
    """Фото товара или заглушка «Нет фото»."""
    pixmap = load_pixmap(relative_path)
    if pixmap is None:
        return product_placeholder(size)
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def avatar_pixmap(relative_path: str | None, name: str, size: int = 64) -> QPixmap:
    """Аватар или круг с буквой."""
    pixmap = load_pixmap(relative_path)
    if pixmap is None:
        return avatar_placeholder(name, size)
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
