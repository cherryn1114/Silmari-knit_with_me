# pages/3_차트_기호_사전.py
# 엑셀에서 뽑아낸 차트 기호 이미지 + 설명 보여주는 페이지

import json
from pathlib import Path

import streamlit as st

BASE = Path(__file__).resolve().parent.parent
JSON_PATH = BASE / "lib" / "chart_symbols.json"
IMG_DIR   = BASE / "assets" / "chart_symbols"

st.set_page_config(
    page_title="실마리 – 차트 기호 사전",
    page_icon="📈",
    layout="wide",
)

st.title("📈 차트 도안 기호 사전")

if not JSON_PATH.exists():
    st.error("`lib/chart_symbols.json` 파일을 찾을 수 없습니다.\n\n터미널에서 `python lib/extract_chart_symbols.py` 를 먼저 실행해 주세요.")
    st.stop()

with JSON_PATH.open(encoding="utf-8") as f:
    data = json.load(f)  # {key: {name, desc, row, image}}

# dict → list 로 변환 (정렬하기 쉽게)
items = []
for key, info in data.items():
    item = {"key": key}
    item.update(info)
    items.append(item)

# 행 번호 기준 정렬
items = sorted(items, key=lambda x: x.get("row", 0))

# 검색 UI
col_search, col_filter = st.columns([3, 1])
with col_search:
    q = st.text_input("검색 (약어, 이름, 설명 등)", "")
with col_filter:
    only_with_img = st.checkbox("이미지 있는 것만", value=True)

def matches(item, q):
    if not q:
        return True
    q = q.lower()
    return (
        q in item["key"].lower()
        or q in str(item.get("name","")).lower()
        or q in str(item.get("desc","")).lower()
    )

filtered = []
for it in items:
    if only_with_img and not it.get("image"):
        continue
    if not matches(it, q):
        continue
    filtered.append(it)

st.caption(f"총 기호: {len(items)}개 · 현재 표시: {len(filtered)}개")

# 카드 형태로 렌더링
for it in filtered:
    key  = it["key"]
    name = it.get("name", "")
    desc = it.get("desc", "")
    img_file = it.get("image", "")

    st.markdown("---")
    st.markdown(f"### 🔹 {key} — {name}")

    cols = st.columns([1, 2])

    # 이미지
    if img_file:
        img_path = IMG_DIR / img_file
        if img_path.exists():
            cols[0].image(str(img_path), use_column_width=True)
        else:
            cols[0].warning("이미지 파일을 찾을 수 없습니다.")
    else:
        cols[0].info("이미지 없음")

    # 설명 텍스트
    if desc:
        cols[1].markdown(desc)
    else:
        cols[1].markdown("_설명 없음_")

st.markdown("---")
st.page_link("HOME.py", label="⬅️ 홈으로")