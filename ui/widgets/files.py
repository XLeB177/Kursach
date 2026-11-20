"""Копирование изображений и сохранение PDF в выбранное место."""
from pathlib import Path
from shutil import copyfile
from uuid import uuid4

from PyQt6.QtGui import QImageReader
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from services import receipts
from services.validators import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def choose_image(parent):
    path, _ = QFileDialog.getOpenFileName(parent, "Выберите изображение", "", "Изображения (*.png *.jpg *.jpeg)")
    return path


def copy_image(source, folder, *, limit=10 * 1024 * 1024):
    source = Path(source)
    suffix = source.suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg") or source.stat().st_size > limit:
        raise ValidationError(f"Выберите PNG или JPG размером до {limit // (1024 * 1024)} МБ")
    reader = QImageReader(str(source))
    size = reader.size()
    if not size.isValid() or size.width() * size.height() > 25_000_000 or reader.read().isNull():
        raise ValidationError("Не удалось открыть изображение или слишком большое разрешение")
    relative = Path("assets") / folder / f"{uuid4().hex}{suffix}"
    (ROOT / relative).parent.mkdir(parents=True, exist_ok=True)
    copyfile(source, ROOT / relative)
    return relative.as_posix()


def discard_image(path):
    if path:
        (ROOT / path).unlink(missing_ok=True)


def download_receipt(parent, actor_id, order_id):
    path, _ = QFileDialog.getSaveFileName(parent, "Сохранить чек", f"chek_{order_id}.pdf", "PDF (*.pdf)")
    if not path:
        return
    if Path(path).suffix.lower() != ".pdf":
        path += ".pdf"
    receipts.save(actor_id, order_id, path)
    QMessageBox.information(parent, "Чек", "Чек сохранён")
