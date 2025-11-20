# pages/3_차트_기호_사전.py
import json
from pathlib import Path

import streamlit as st

# -----------------------------
# 설정
# -----------------------------
st.set_page_config(
    page_title="실마리 — 차트 기호 사전",
    page_icon="🧶",
    layout="wide",
)

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "assets" / "chart_from_excel" / "manifest.json"

# 엑셀 시트(소분류) 순서 고정
SHEET_ORDER = [
    "1코 기호",
    "1코 2단 기호",
    "2코 교차뜨기",
    "3코 교차뜨기",
    "4코 교차뜨기",
    "5코 교차뜨기",
    "6코 교차뜨기",
    "7코 교차뜨기",
    "8코 교차뜨기",
    "10코 교차뜨기",
    "3코 방울뜨기",
    "5코 방울뜨기",
    "교차뜨기 일본식 기호",
    "노트뜨기",
]

# -----------------------------
# 데이터 로드
# -----------------------------
def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        st.error(f"매니페스트 파일을 찾을 수 없습니다: {MANIFEST_PATH}")
        return {}

    with MANIFEST_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    # 시트 순서를 우리가 원하는 순서로 정렬
    ordered = {}
    for name in SHEET_ORDER:
        if name in data:
            ordered[name] = data[name]
    for name in data.keys():
        if name not in ordered:
            ordered[name] = data[name]

    return ordered


manifest = load_manifest()

# -----------------------------
# UI 상단
# -----------------------------
st.title("🧵 차트 기호 사전")

if not manifest:
    st.stop()

sheet_names = list(manifest.keys())

choice = st.selectbox(
    "소분류(엑셀 시트) 선택",
    options=["전체 보기"] + sheet_names,
)

# 보여줄 시트 목록
target_sheets = sheet_names if choice == "전체 보기" else [choice]

total_icons = sum(len(manifest[s]["items"]) for s in target_sheets)
st.caption(f"현재 표시되는 기호 수: **{total_icons}개**")

# -----------------------------
# 렌더링 함수
# -----------------------------
def show_sheet(sheet_title: str, data: dict):
    img_dir = ROOT / data["img_dir"]
    items = data.get("items", [])

    st.markdown(f"### 🧵 {sheet_title} · {len(items)}개")

    if not img_dir.exists():
        st.warning(f"이미지 폴더를 찾을 수 없습니다: {img_dir}")
        return

    cols = st.columns(6)
    col_idx = 0

    for item in items:
        file_name = item.get("file", "")
        name = (item.get("abbr", "") or "").strip()
        desc = (item.get("desc", "") or "").strip()

        img_path = img_dir / file_name
        col = cols[col_idx % 6]

        with col:
            if img_path.exists():
                # use_container_width 안 씀 → 노란 경고 없음
                st.image(str(img_path), width=110)

            # 파일명은 얇은 회색 캡션
            st.caption(file_name)

            # 이름(+설명)을 굵게
            if name or desc:
                label = name
                if desc:
                    # SSK (오른코 겹쳐 코 모아뜨기) 이런 식으로 표시
                    label = f"{name} ({desc})" if name else desc
                st.markdown(f"**{label}**")

        col_idx += 1
        if col_idx % 6 == 0 and col_idx < len(items):
            cols = st.columns(6)

    st.divider()


# -----------------------------
# 실제 표시
# -----------------------------
for sheet in target_sheets:
    show_sheet(sheet, manifest[sheet])

st.page_link("HOME.py", label="⬅ 홈으로")