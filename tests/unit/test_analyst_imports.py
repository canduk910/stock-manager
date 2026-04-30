"""REQ-ANALYST-13: requirements + import 검증."""


def test_pdfplumber_importable():
    import pdfplumber  # noqa: F401


def test_stock_analyst_pdf_importable():
    from stock.analyst_pdf import summarize_one  # noqa: F401


def test_analyst_report_model_exported():
    from db.models import AnalystReport  # noqa: F401


def test_analyst_repository_exported():
    from db.repositories import AnalystRepository  # noqa: F401
