"""Точка входа: пустое окно приложения, журнал и перехват ошибок."""

import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

_ROOT = Path(__file__).resolve().parent
_LOG_DIR = _ROOT / "logs"
_LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=_LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
_logger = logging.getLogger("board_games_shop")


def _show_error(message: str) -> None:
    """Понятное окно вместо падения. Без traceback."""
    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle("Ошибка")
    box.setText("Произошла непредвиденная ошибка. Подробности записаны в журнал.")
    box.setInformativeText(message)
    box.exec()


def handle_exception(exc_type, exc_value, exc_traceback) -> None:
    """Глобальный перехват необработанных исключений."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    _logger.exception(
        "Необработанное исключение",
        exc_info=(exc_type, exc_value, exc_traceback),
    )
    if QApplication.instance() is not None:
        _show_error(str(exc_value) or "Неизвестная ошибка.")


def main() -> None:
    sys.excepthook = handle_exception
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Магазин настольных игр")
    window.resize(800, 600)
    window.show()
    _logger.info("Приложение запущено")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
