# lib/upload_utils.py
# 파일 업로드 + 간단한 히스토리(새로고침/페이지 이동 후에도 마지막 파일 유지)

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Tuple, Optional

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

# 업로드된 파일을 저장할 기본 폴더
UPLOAD_ROOT = Path("data/uploads")


def _ensure_root() -> None:
    """업로드 루트 폴더가 없으면 생성."""
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _get_types(accept: Literal["any", "pdf", "image", "excel", "pattern"]) -> Optional[list[str]]:
    """
    Streamlit file_uploader 에 넘길 type 리스트.
    ❗ 여기에는 'PATTERN_PDF' 같은 커스텀 문자열이 들어가면 안 되고,
       반드시 실제 확장자만 들어가야 함.
    """
    if accept == "pdf":
        return ["pdf"]
    if accept == "image":
        return ["png", "jpg", "jpeg", "gif"]
    if accept == "excel":
        return ["xlsx", "xls"]
    if accept == "pattern":
        # 도안용: pdf + 이미지 모두 허용
        return ["pdf", "png", "jpg", "jpeg"]
    # any  또는 그 외 값 → 제한 없음
    return None


def uploader_with_history(
    key: str,
    label: str,
    accept: Literal["any", "pdf", "image", "excel", "pattern"] = "any",
    subdir: str | None = None,
) -> Tuple[Optional[UploadedFile], Optional[str]]:
    """
    공용 업로더 함수.

    - key: 페이지별 / 용도별 고유 키 (예: "pattern_pdf", "tech_abbr_pdf")
    - label: 업로더에 표시될 라벨 텍스트
    - accept:
        - "pdf"     → pdf만
        - "image"   → png/jpg/jpeg/gif
        - "excel"   → xlsx/xls
        - "pattern" → pdf + 이미지
        - "any"     → 모든 파일
    - subdir: data/uploads 아래의 하위 폴더 이름 (없으면 data/uploads 바로 아래에 저장)

    리턴:
        (현재 업로드된 UploadedFile 객체 또는 None,
         디스크에 저장된 파일 경로(str) 또는 None)
    """
    _ensure_root()

    types = _get_types(accept)

    # Streamlit 위젯 키는 겹치면 안 되어서 _uploader suffix를 붙여 줌
    widget_key = f"{key}_uploader"

    uploaded: UploadedFile | None = st.file_uploader(
        label,
        type=types,
        key=widget_key,
    )

    # 세션 상태 초기화
    if "uploaded_files" not in st.session_state:
        st.session_state["uploaded_files"] = {}

    saved_path: Optional[str] = None

    # 새 파일이 올라왔을 경우 → 디스크에 저장 + 세션에 경로 기록
    if uploaded is not None:
        target_dir = UPLOAD_ROOT
        if subdir:
            target_dir = target_dir / subdir

        target_dir.mkdir(parents=True, exist_ok=True)

        filename = uploaded.name
        # 같은 이름이 이미 있으면 덮어쓰기
        dest = target_dir / filename

        with open(dest, "wb") as f:
            f.write(uploaded.getbuffer())

        saved_path = str(dest)
        st.session_state["uploaded_files"][key] = saved_path

    else:
        # 이번에 새로 올린 건 없지만, 예전에 올린 경로가 있으면 그대로 사용
        prev = st.session_state.get("uploaded_files", {}).get(key)
        if prev and Path(prev).exists():
            saved_path = prev

    # 현재 사용 중인 파일 경로를 화면에 보여주기 (선택사항)
    if saved_path:
        st.success(f"현재 사용 중인 파일: `{Path(saved_path).name}`")
    else:
        st.info("아직 선택된 파일이 없습니다.")

    return uploaded, saved_path