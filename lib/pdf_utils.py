# lib/pdf_utils.py
# PyMuPDF(fitz) 안전 사용 / PDF 아닐 때 처리 / 에러 메시지 개선

from typing import List
import fitz  # pip package name: pymupdf

def is_pdf_bytes(b: bytes) -> bool:
    # 간단한 시그니처 검사 (예: '%PDF')
    if not b or len(b) < 4:
        return False
    try:
        head = b[:4]
        return head == b"%PDF"
    except Exception:
        return False

def extract_text_per_page(pdf_bytes: bytes) -> List[str]:
    """
    PDF 바이트에서 페이지별 텍스트 추출
    - PDF가 아니면 ValueError
    - 암호/손상 등 예외는 그대로 raise
    """
    if not is_pdf_bytes(pdf_bytes):
        raise ValueError("PDF 파일이 아닌 것 같습니다. 업로드한 파일 형식을 확인하세요.")
    texts: List[str] = []
    # stream+filetype='pdf' 방식은 byte 입력에 안전
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            # 필요에 따라 "text", "blocks", "rawdict" 등 교체 가능
            texts.append(page.get_text("text"))
    return texts