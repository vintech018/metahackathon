"""
file_parser.py — File input support for Bug Bounty Vulnerability Triage.

Extracts text content from supported file types (.py, .java, .txt, .pdf)
for use in the existing LLM triage pipeline.
"""

import os


def extract_text(file_path: str) -> str:
    """
    Extract text content from a supported file.

    Supported extensions:
        .py, .java, .txt  — read as plain text (UTF-8)
        .pdf               — extract text using PyPDF2

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the input file.

    Returns
    -------
    str
        Extracted text content, or empty string if unsupported / unreadable.
    """
    if not file_path or not os.path.isfile(file_path):
        return ""

    ext = os.path.splitext(file_path)[1].lower()

    # ── Plain-text file types ─────────────────────────────────────────────
    if ext in (".py", ".java", ".txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            return ""

    # ── PDF extraction ────────────────────────────────────────────────────
    if ext == ".pdf":
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
            return text
        except Exception:
            return ""

    # ── Unsupported extension ─────────────────────────────────────────────
    return ""
