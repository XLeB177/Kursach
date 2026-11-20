"""Запуск приложения и обработка неожиданных ошибок."""
import logging
import sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox

from ui.windows.shop import ShopWindow

LOG_DIR = Path(__file__).resolve().parent / "logs"
logger = logging.getLogger("board_games_shop")


def handle_exception(exc_type, exc_value, exc_traceback):
    if not issubclass(exc_type, Exception):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    frames = traceback.extract_tb(exc_traceback)
    location = " → ".join(f"{Path(frame.filename).name}:{frame.lineno}" for frame in frames)
    logger.error("%s (%s)", exc_type.__name__, location)
    if QApplication.instance():
        QMessageBox.critical(None, "Ошибка", "Произошла непредвиденная ошибка. Повторите действие.")


def main():
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=LOG_DIR / "app.log", level=logging.INFO, encoding="utf-8",
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    sys.excepthook = handle_exception
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ShopWindow()
    window.show()
    logger.info("Приложение запущено")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
