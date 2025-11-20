# pages/3_차트_기호_사전.py
import json
import re
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

# 엑셀 시트 순서 고정
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
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    ordered = {name: data[name] for name in SHEET_ORDER if name in data}
    for name in data.keys():
        if name not in ordered:
            ordered[name] = data[name]

    return ordered


manifest = load_manifest()


# -----------------------------
# 이름 정리 함수
# -----------------------------
def clean_name(raw: str) -> str:
    """
    예)
      'chart_001.png (겉뜨기)' → '겉뜨기'
      'chart_022.png(M1R)'     → 'M1R'
      'SSK(오른코 겹쳐 2코 모아뜨기)' → 'SSK(오른코 겹쳐 2코 모아뜨기)' (chart_XXX 없으면 그대로)
    """
    if not raw:
        return ""

    # 1) chart_000.png 부분 제거
    s = re.sub(r"chart_\d+\.png\s*", "", raw).strip()

    # 2) 남은 게 괄호만 있으면 괄호 제거
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()

    return s


# -----------------------------
# UI
# -----------------------------
st.title("🧵 차트 기호 사전")

sheet_names = list(manifest.keys())
choice = st.selectbox("소분류(엑셀 시트) 선택", ["전체 보기"] + sheet_names)

target_sheets = sheet_names if choice == "전체 보기" else [choice]
total_icons = sum(len(manifest[s]["items"]) for s in target_sheets)
st.caption(f"현재 표시되는 기호 수: **{total_icons}개**")


# -----------------------------
# 렌더링 함수
# -----------------------------
def show_sheet(sheet_title: str, data: dict):
    img_dir = ROOT / data["img_dir"]
    items = data["items"]

    st.markdown(f"### 🧵 {sheet_title} · {len(items)}개")

    cols = st.columns(6)
    col_idx = 0

    for item in items:
        file_name = item.get("file", "")
        raw_name = (item.get("abbr", "") or "").strip()
        desc = (item.get("desc", "") or "").strip()
        img_path = img_dir / file_name

        name = clean_name(raw_name)

        col = cols[col_idx % 6]

        with col:
            if img_path.exists():
                st.image(str(img_path), width=110)

            # ⛔ 파일명은 더 이상 표시하지 않음
            # st.caption(file_name)

            # ✅ 기호 이름 / 설명만 굵게 표시
            label = ""
            if name and desc and desc != name:
                label = f"{name} ({desc})"
            elif name:
                label = name
            elif desc:
                label = desc

            if label:
                st.markdown(f"**{label}**")

        col_idx += 1
        if col_idx % 6 == 0 and col_idx < len(items):
            cols = st.columns(6)

    st.divider()


# -----------------------------
# 시트별 렌더링
# -----------------------------
for sheet in target_sheets:
    show_sheet(sheet, manifest[sheet])

st.page_link("HOME.py", label="⬅ 홈으로")