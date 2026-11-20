"""Формирование PDF-чека с кириллицей."""
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.sax.saxutils import escape

from services.calculations import line_total, totals
from services.validators import ValidationError

FONT = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "DejaVuSans.ttf"


def write_receipt(order, items, target):
    if not FONT.is_file():
        raise ValidationError("Не найден шрифт для чека")

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise ValidationError("Установите ReportLab для сохранения PDF-чека") from exc

    font = "DejaVuSans"
    try:
        pdfmetrics.registerFont(TTFont(font, str(FONT)))
    except Exception as exc:
        raise ValidationError("Не удалось прочитать шрифт для чека") from exc

    body = ParagraphStyle("Body", fontName=font, fontSize=10, leading=15, splitLongWords=True)
    heading = ParagraphStyle("Heading", parent=body, fontSize=16, leading=22)

    def number(value):
        return f"{value:,.2f}".replace(",", " ").replace(".", ",")

    def paragraph(value, style=body):
        return Paragraph(escape(str(value)), style)

    count, total = totals(items)
    rows = [["№", "Наименование", "Цена", "Кол-во", "Сумма"]]
    for index, item in enumerate(items, 1):
        rows.append([
            index, paragraph(item["name"]), number(item["price"]), item["quantity"],
            number(line_total(item["price"], item["quantity"])),
        ])
    table = Table(rows, colWidths=(27, 211, 76, 52, 85), repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4ebe8")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))
    story = [
        paragraph("Магазин настольных игр"),
        paragraph(f"Чек по заказу № {order['id']}", heading),
        paragraph(order["created_at"].strftime("%d.%m.%Y %H:%M")),
        paragraph(f"Покупатель: {order['name']} ({order['email']})"),
        Spacer(1, 14), table, Spacer(1, 14),
        paragraph(f"Всего единиц товара: {count}"),
        paragraph(f"Итого: {number(total)} руб.", heading),
    ]

    target = Path(target)
    temporary = None
    try:
        with NamedTemporaryFile(dir=target.parent, suffix=".pdf", delete=False) as file:
            temporary = Path(file.name)
        SimpleDocTemplate(str(temporary), pagesize=A4, title=f"Чек по заказу № {order['id']}").build(story)
        temporary.replace(target)
    except OSError as exc:
        raise ValidationError("Не удалось сохранить чек. Проверьте место и права на запись") from exc
    finally:
        if temporary and temporary.exists():
            temporary.unlink(missing_ok=True)
