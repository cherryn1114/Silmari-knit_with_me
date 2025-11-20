# lib/pdf_utils.py

from pathlib import Path
from typing import Union

PdfPath = Union[str, Path]


def extract_pdf_text(path: PdfPath) -> str:
    """
    PDF 파일에서 모든 텍스트를 추출해서 하나의 문자열로 반환합니다.
    """
    from PyPDF2 import PdfReader  # requirements.txt 에 PyPDF2가 있어야 합니다.

    p = Path(path)
    reader = PdfReader(str(p))

    chunks: list[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt:
            chunks.append(txt)

    return "\n".join(chunks)


# 예전 이름 호환용 별칭 (import 에서 이 이름을 써도 동작하게)
def extract_pdf_text_from_pdf(path: PdfPath) -> str:
    return extract_pdf_text(path)


__all__ = ["extract_pdf_text", "extract_pdf_text_from_pdf"]