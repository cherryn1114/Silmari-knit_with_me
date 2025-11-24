# lib/upload_utils.py
from __future__ import annotations

import streamlit as st
from pathlib import Path

# 업로드 파일이 저장될 폴더
UPLOAD_DIR = Path("data/uploads")


def _ensure_upload_dir() -> None:
    """업로드 폴더 없으면 생성."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def list_uploaded_files() -> list[Path]:
    """저장된 업로드 파일 전체 목록."""
    _ensure_upload_dir()
    return sorted(
        [p for p in UPLOAD_DIR.iterdir() if p.is_file()],
        key=lambda p: p.name,
    )


def save_uploaded_file(uploaded_file) -> Path:
    """
    Streamlit UploadedFile -> 디스크에 저장하고 Path 반환.
    같은 이름이 있을 경우, _1, _2 ... 붙여서 중복 회피.
    """
    _ensure_upload_dir()

    original_name = uploaded_file.name
    base = Path(original_name).stem
    suffix = Path(original_name).suffix

    dst = UPLOAD_DIR / original_name
    counter = 1
    while dst.exists():
        dst = UPLOAD_DIR / f"{base}_{counter}{suffix}"
        counter += 1

    with open(dst, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return dst


def uploader_with_history(
    label: str,
    type: list[str] | None = None,
    key: str = "file_uploader",
) -> Path | None:
    """
    업로더 + 기존 업로드 파일 선택까지 한 번에 제공하는 헬퍼.

    - 새 파일을 업로드하면 data/uploads/ 밑에 저장
    - 이미 저장된 파일들 중 하나를 selectbox로 선택 가능
    - 반환값: 선택된 파일의 Path (선택 안 했으면 None)
    """
    _ensure_upload_dir()

    st.markdown(f"**{label}**")

    # 1) 새 파일 업로드
    uploaded = st.file_uploader(
        "새 파일 업로드",
        type=type,
        key=key,
    )

    newest_path: Path | None = None
    if uploaded is not None:
        newest_path = save_uploaded_file(uploaded)
        st.success(f"📁 파일이 저장되었습니다: `{newest_path.name}`")

    # 2) 기존 업로드 파일 목록
    files = list_uploaded_files()
    if not files:
        st.info("아직 업로드된 파일이 없습니다. 위에서 파일을 업로드해 보세요.")
        return newest_path

    options = ["(파일 선택 안 함)"] + [f.name for f in files]

    # 방금 올린 파일이 있으면 그걸 기본 선택으로
    if newest_path is not None:
        try:
            default_index = 1 + [f.name for f in files].index(newest_path.name)
        except ValueError:
            default_index = 0
    else:
        default_index = 0

    selected_label = st.selectbox(
        "이미 업로드해 둔 파일 중에서 사용할 파일 선택",
        options,
        index=default_index,
        key=f"{key}_select",
    )

    if selected_label == "(파일 선택 안 함)":
        return newest_path

    for f in files:
        if f.name == selected_label:
            return f

    return newest_path