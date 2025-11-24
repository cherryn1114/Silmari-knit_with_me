# lib/pdf_utils.py
# PDF에서 텍스트 추출 관련 유틸 함수 모음

from __future__ import annotations

from pathlib import Path
from typing import Union

import pypdf
from streamlit.runtime.uploaded_file_manager import UploadedFile


PathLike = Union[str, Path]


def _read_pdf_from_path(path: PathLike) -> str:
    """
    로컬 경로에 저장된 PDF 파일에서 텍스트를 추출해서 하나의 문자열로 돌려줍니다.
    pypdf 가 까다로운 PDF 를 만나더라도 최대한 에러 없이 진행하도록 예외를 잡아줍니다.
    """
    pdf_path = Path(path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    text_chunks: list[str] = []

    # strict=False 로 설정해서 조금 깨진 PDF 도 최대한 읽도록 함
    with pdf_path.open("rb") as f:
        try:
            reader = pypdf.PdfReader(f, strict=False)
        except Exception as e:  # 구조가 완전히 깨진 경우
            # 상위 코드에서 에러 메시지를 보여줄 수 있도록 그대로 올려 보냄
            raise RuntimeError(f"PDF 읽기 오류: {e}") from e

        # 어떤 이유로든 root 가 None 인 경우를 대비
        try:
            pages = reader.pages
        except Exception as e:
            raise RuntimeError(f"PDF 페이지 정보 읽기 오류: {e}") from e

        for page in pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            text_chunks.append(page_text)

    return "\n".join(text_chunks).strip()


def _read_pdf_from_uploaded(uploaded: UploadedFile, save_to: PathLike | None = None) -> str:
    """
    Streamlit UploadedFile 객체에서 직접 텍스트를 추출합니다.
    (지금은 page 5 에서는 경로 기반 함수를 쓰고 있어서, 이 함수는
     혹시 다른 페이지에서 쓸 일이 생길 때를 대비해서 남겨둔 헬퍼예요.)
    """
    # 필요하면 임시 파일로 저장해서 _read_pdf_from_path 재사용
    if save_to is None:
        tmp_path = Path("data/uploads") / uploaded.name
    else:
        tmp_path = Path(save_to)

    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    with tmp_path.open("wb") as f:
        f.write(uploaded.getbuffer())

    return _read_pdf_from_path(tmp_path)


def extract_pdf_text(pdf_source: Union[PathLike, UploadedFile]) -> str:
    """
    공용 진입점 함수.

    - pdf_source 가 문자열/Path 이면: 파일 경로로 간주하고 읽기
    - pdf_source 가 UploadedFile 이면: 임시로 저장 후 읽기
    """
    if isinstance(pdf_source, (str, Path)):
        return _read_pdf_from_path(pdf_source)

    # Streamlit UploadedFile 인 경우
    if isinstance(pdf_source, UploadedFile):
        return _read_pdf_from_uploaded(pdf_source)

    raise TypeError(
        f"지원하지 않는 타입입니다: {type(pdf_source)}. "
        "경로(str/Path) 또는 Streamlit UploadedFile 만 사용할 수 있습니다."
    )