"""Question-bank importers."""

__all__ = ["ImportReport", "parse_question_bank"]


def __getattr__(name: str):
    if name == "parse_question_bank":
        from .docx_question_bank import parse_question_bank

        return parse_question_bank
    if name == "ImportReport":
        from .report import ImportReport

        return ImportReport
    raise AttributeError(name)
