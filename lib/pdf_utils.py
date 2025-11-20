# lib/pdf_utils.py
# PDF에서 텍스트를 추출하기 위한 유틸 함수 모음
# - 1차: PyPDF2
# - 2차: pdfminer.six
#
# 사용 예시:
#   from lib.pdf_utils import extract_pdf_text_from_pdf
#   text = extract_pdf_text_from_pdf("path/to/file.pdf")

from __future__ import annotations

from pathlib import Path


# --------------------------------------------------------------------
# 1) PyPDF2 백엔드
# --------------------------------------------------------------------
def _extract_with_pypdf(pdf_path: Path) -> str:
    """
    PyPDF2로 텍스트를 추출한다.
    라이브러리가 없거나 실패하면 빈 문자열을 반환.
    """
    try:
        from PyPDF2 import PdfReader
    except Exception:
        # PyPDF2가 설치 안 되어 있으면 빈 문자열
        return ""

    try:
        reader = PdfReader(str(pdf_path))
        texts = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            texts.append(t)
        return "\n".join(texts)
    except Exception:
        return ""


# --------------------------------------------------------------------
# 2) pdfminer.six 백엔드
# --------------------------------------------------------------------
def _extract_with_pdfminer(pdf_path: Path) -> str:
    """
    pdfminer.six로 텍스트를 추출한다.
    패키지가 없거나 실패하면 빈 문자열을 반환.
    """
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract_text
    except Exception:
        return ""

    try:
        text = pdfminer_extract_text(str(pdf_path)) or ""
        return text
    except Exception:
        return ""


# --------------------------------------------------------------------
# 3) 품질 체크 & 메인 함수
# --------------------------------------------------------------------
def _looks_garbled(text: str) -> bool:
    """
    추출된 텍스트가 '심하게 깨진 것'처럼 보이면 True.
    (아주 단순한 휴리스틱 – pdfminer를 한 번 더 시도할지 결정하는 용도)
    """
    if not text:
        return True

    # 너무 짧으면 의미있는 텍스트가 아닐 가능성이 높다고 가정
    if len(text) < 50:
        return True

    # 비인쇄 제어문자가 너무 많은 경우
    bad = sum(1 for ch in text if ord(ch) < 9 or (13 < ord(ch) < 32))
    if bad / len(text) > 0.05:
        return True

    return False


def extract_pdf_text_from_pdf(path: str | Path) -> str:
    """
    PDF 파일에서 텍스트를 추출해 문자열로 반환.
    - 1차: PyPDF2 사용
    - 1차 결과가 너무 짧거나/깨진 것 같으면 2차: pdfminer.six 사용
    - 둘 다 실패하면 가능한 결과(또는 빈 문자열)를 반환
    """
    pdf_path = Path(path)

    # 1차: PyPDF2
    text1 = _extract_with_pypdf(pdf_path).strip()

    if text1 and not _looks_garbled(text1):
        return text1

    # 2차: pdfminer.six
    text2 = _extract_with_pdfminer(pdf_path).strip()
    if text2:
        return text2

    # 둘 다 실패하면 1차 결과라도 돌려준다(또는 빈 문자열)
    return text1


# 옛 코드 호환용: 예전 이름을 그대로 쓸 수 있게 래퍼 제공
def extract_pdf_text(path: str | Path) -> str:
    """
    이전 코드에서 사용하던 이름. extract_pdf_text_from_pdf와 동일.
    """
    return extract_pdf_text_from_pdf(path)