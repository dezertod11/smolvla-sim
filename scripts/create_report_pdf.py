"""Create the one-page submission report from committed results."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf/smolvla_report.pdf"


def register_fonts():
    """Register a Cyrillic font on Windows and common Linux distributions."""
    candidates = [
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
    ]
    for regular, bold in candidates:
        if regular.is_file() and bold.is_file():
            pdfmetrics.registerFont(TTFont("Report", regular))
            pdfmetrics.registerFont(TTFont("Report-Bold", bold))
            return
    raise FileNotFoundError("Arial or DejaVu Sans is required to build the report")


def main():
    register_fonts()
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Report",
        fontSize=8.2,
        leading=10.2,
        spaceAfter=2.5 * mm,
    )
    heading = ParagraphStyle(
        "Heading",
        parent=body,
        fontName="Report-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=1 * mm,
        spaceAfter=1 * mm,
    )
    title = ParagraphStyle(
        "Title",
        parent=body,
        fontName="Report-Bold",
        fontSize=17,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle = ParagraphStyle(
        "Subtitle",
        parent=body,
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
    )
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=11 * mm,
        rightMargin=11 * mm,
        topMargin=9 * mm,
        bottomMargin=9 * mm,
    )
    story = [
        Paragraph("SmolVLA + LeRobot + ROS2 в LIBERO", title),
        Paragraph("Краткий отчёт о решении и проверенных результатах", subtitle),
        Spacer(1, 3 * mm),
    ]
    metrics = Table(
        [
            ["Собственная BF16", "Reference BF16", "Обучение", "ROS2 Compose"],
            ["97/100", "87/100", "30 000 шагов", "success=True"],
        ],
        colWidths=[47 * mm] * 4,
    )
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
                ("FONTNAME", (0, 0), (-1, 0), "Report-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Report-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([metrics, Spacer(1, 2.5 * mm)])
    charts = Table(
        [[
            Image(str(ROOT / "artifacts/results/training/loss.png"), 89 * mm, 41 * mm),
            Image(
                str(ROOT / "artifacts/results/summary/evaluation_comparison.png"),
                99 * mm,
                41 * mm,
            ),
        ]],
        colWidths=[91 * mm, 101 * mm],
    )
    charts.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.extend([charts, Spacer(1, 1.5 * mm)])
    story.extend(
        [
            Paragraph("Данные и обучение", heading),
            Paragraph(
                "Использованы 454 демонстрации <b>libero_object</b> (66 984 кадра, "
                "10 задач). Камеры согласованы явным <b>rename_map</b>. Обучение: seed "
                "42, batch 16, AdamW 1e-4, 1 000 шагов warm-up, 30 000 шагов, BF16 "
                "AMP. VLM и vision encoder заморожены; обучаются action expert и "
                "проекции - 99 880 992 из 450 046 176 параметров. Loss снизился с "
                "0,545 до 0,047; checkpoint повторно загружен и проверен forward.",
                body,
            ),
            Paragraph("Оценка и квантизация", heading),
            Paragraph(
                "Все варианты оценены на одинаковых seed: 10 задач по 10 эпизодов. "
                "Для собственной BF16-модели n_action_steps=1/10/50 дал 85%/97%/71%; "
                "reference BF16 n=10 - 87%. GPU latency BF16 p50/p95: "
                "155,83/156,90 мс. INT8 уменьшил размер с 906,7 до 548,2 МБ и peak "
                "memory с 993,3 до 651,2 МБ, но замедлил p50 до 363,40 мс и получил "
                "0/100. Для Jetson Orin 16 ГБ выбран BF16, n_action_steps=10.",
                body,
            ),
            Paragraph("ROS2, Docker и ограничения", heading),
            Paragraph(
                "sim_node публикует две камеры и состояние, принимает /vla/action; "
                "smolvla_node выполняет single-flight inference в отдельном worker. "
                "Checkpoint, instruction, precision, device и частоты задаются YAML. "
                "На RTX 5070 Ti Compose closed loop завершился success=True после 159 "
                "действий и вернул код 0. 46 CPU-тестов, Ruff и GitHub Actions зелёные. "
                "Ограничение: результаты относятся к LIBERO; sim-to-real и Orin требуют "
                "отдельной калибровки, safety layer и аппаратной проверки.",
                body,
            ),
        ]
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
