# lib/upload_utils.py
# ---------------------------------------------
# 여러 페이지에서 공통으로 쓰는 "업로드 + 히스토리" 유틸
#
# - 파일은 항상 data/uploads/ 아래에 저장합니다.
# - key(예: 'pattern_pdf') 별로 최근 업로드 목록을 기억합니다.
# - 이전에 올린 파일을 selectbox에서 다시 선택해 쓸 수 있습니다.
# - streamlit 의 file_uploader 옵션(type, accept, help 등)을
#   잘못 넘겨도 에러 나지 않도록 **kwargs 를 받아서 무시합니다.
# ---------------------------------------------

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st

# 업로드 파일이 저장될 기본 폴더
UPLOAD_ROOT = Path("data/uploads")
INDEX_PATH = UPLOAD_ROOT / "index.json"


# 내부 유틸 함수들 ------------------------------------


def _ensure_upload_dir() -> None:
    """data/uploads 폴더가 없으면 만든다."""
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _load_index() -> Dict[str, List[Dict[str, Any]]]:
    """업로드 히스토리 index.json 읽기 (없으면 빈 dict)."""
    _ensure_upload_dir()

    if not INDEX_PATH.exists():
        return {}

    try:
        with INDEX_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # 깨졌거나 형식이 이상하면 새로 시작
        return {}

    # 예전에 list 형태로 잘못 저장됐을 수도 있으니 방어
    if not isinstance(data, dict):
        return {}

    # key 별 value 는 항상 list 여야 한다.
    fixed: Dict[str, List[Dict[str, Any]]] = {}
    for k, v in data.items():
        if isinstance(v, list):
            fixed[k] = [x for x in v if isinstance(x, dict)]
    return fixed


def _save_index(index: Dict[str, List[Dict[str, Any]]]) -> None:
    """업로드 히스토리 index.json 저장."""
    _ensure_upload_dir()
    with INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _save_uploaded_file(uploaded_file, dest_path: Path) -> None:
    """Streamlit UploadedFile 을 지정된 경로에 저장."""
    with dest_path.open("wb") as out:
        out.write(uploaded_file.getbuffer())


def _build_history_entry(name: str, path: str, size: int) -> Dict[str, Any]:
    return {
        "name": name,
        "path": path,
        "size": size,
    }


# 공개 함수 -------------------------------------------


def uploader_with_history(
    key: str,
    label: str = "파일 업로드",
    **kwargs: Any,
) -> Tuple[Any, str | None]:
    """
    파일 업로드 + 히스토리 관리 위젯.

    Parameters
    ----------
    key : str
        업로드 그룹 구분용 키 (예: 'pattern_pdf', 'abbr_pdf' 등)
    label : str
        업로더에 표시할 라벨 텍스트

    나머지 인자(**kwargs)는 무시해서,
    type / accept / help 등을 잘못 넘겨도 에러가 나지 않도록 했다.

    Returns
    -------
    (uploaded_file, current_path)
        uploaded_file : 이번 실행에서 막 업로드한 Streamlit UploadedFile 객체 또는 None
        current_path  : 현재 선택된(사용 중인) 파일의 로컬 경로 (없으면 None)
    """
    _ensure_upload_dir()
    index = _load_index()
    history: List[Dict[str, Any]] = index.get(key, [])

    st.write("")  # 약간의 여백

    # 1) 새 파일 업로드 --------------------------------
    uploaded_file = st.file_uploader(label, key=f"{key}_uploader")

    new_entry: Dict[str, Any] | None = None
    if uploaded_file is not None:
        # 같은 이름이면 뒤에 번호 붙이기
        original_name = uploaded_file.name
        dest = UPLOAD_ROOT / original_name
        base = dest.stem
        suffix = dest.suffix
        counter = 1
        while dest.exists():
            dest = UPLOAD_ROOT / f"{base}_{counter}{suffix}"
            counter += 1

        _save_uploaded_file(uploaded_file, dest)
        rel_path = str(dest)

        new_entry = _build_history_entry(
            name=os.path.basename(rel_path),
            path=rel_path,
            size=uploaded_file.size,
        )

        # 히스토리 맨 앞에 추가 (동일 path 는 제거)
        history = [h for h in history if h.get("path") != rel_path]
        history.insert(0, new_entry)
        index[key] = history
        _save_index(index)

        st.success(f"PDF 파일이 업로드되었습니다.\n\n`{rel_path}`")

    # 2) 이전 업로드 목록에서 선택 ----------------------
    current_path: str | None = None

    if history:
        options = [h["name"] for h in history]
        # 방금 업로드했다면 그걸 기본값으로 선택
        default_index = 0
        if new_entry is not None:
            try:
                default_index = options.index(new_entry["name"])
            except ValueError:
                default_index = 0

        selected_name = st.selectbox(
            "이전에 업로드한 파일 중에서 사용할 파일을 선택하세요.",
            options,
            index=default_index,
            key=f"{key}_history",
        )

        for h in history:
            if h["name"] == selected_name:
                current_path = h["path"]
                break

        if current_path:
            st.info(f"현재 사용 중인 파일: `{selected_name}`\n\n경로: `{current_path}`")
    else:
        st.info("아직 업로드된 파일이 없습니다. 먼저 위에 PDF 를 업로드하세요.")

    return uploaded_file, current_path