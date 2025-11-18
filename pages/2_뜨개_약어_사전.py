# pages/2_뜨개_약어_사전.py

import json
from pathlib import Path
import streamlit as st
from lib import parser
from lib.utils import get_youtube_thumbnail


st.title("🧶 뜨개 약어 사전 (대형 썸네일 + YouTube 링크)")

BASE_PATH = "symbols.json"
EXTRA_PATH = "symbols_extra.json"


# ----------------------------------------
# JSON 안전 로딩
# ----------------------------------------
def load_json_safe(filename: str) -> dict:
    try:
        return parser.load_lib(filename)
    except:
        return {}


base = load_json_safe(BASE_PATH)
extra = load_json_safe(EXTRA_PATH)

# 병합
merged = {**base, **extra}


# ----------------------------------------
# 영상에서 '개별 영상 링크만' 추출
# ----------------------------------------
def pick_video(vlist):
    if not isinstance(vlist, list):
        return ""

    for v in vlist:
        url = (v.get("url") or "").strip()
        if not url:
            continue

        # playlist 단독 제외
        if "list=" in url and "watch?v=" not in url and "youtu.be" not in url:
            continue

        return url

    return ""


# ----------------------------------------
# 검색 UI
# ----------------------------------------
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    q = st.text_input("검색 (약어/영문/한글/설명 검색)", "")

with col2:
    only_new = st.checkbox("추가된 항목만 보기(symbols_extra)", False)

with col3:
    only_video = st.checkbox("영상 있는 항목만", False)


# 필터링
def match(x):
    return q.lower() in str(x).lower()


filtered = {}

for key, item in merged.items():
    if q:
        if not (
            match(key)
            or match(item.get("name_en", ""))
            or match(item.get("name_ko", ""))
            or match(item.get("desc_ko", ""))
            or any(match(a) for a in item.get("aliases", []))
        ):
            continue

    if only_new and key not in extra:
        continue

    video = pick_video(item.get("videos", []))
    if only_video and not video:
        continue

    filtered[key] = item


st.write(f"총 **{len(filtered)}개** 용어 표시")


# ----------------------------------------
# 카드 렌더링 (썸네일 크게)
# ----------------------------------------
for key, item in filtered.items():
    st.markdown("---")
    st.markdown(f"## 🔹 **{key}** — {item.get('name_en','')} / {item.get('name_ko','')}")

    st.write(item.get("desc_ko", "(설명 없음)"))

    video = pick_video(item.get("videos", []))
    if video:
        thumb = get_youtube_thumbnail(video)

        if thumb:
            st.image(thumb, width=350)  # 🔥 여기서 크기 조절 (350~500 추천)

        st.markdown(f"👉 **[영상 보기]({video})**", unsafe_allow_html=True)
    else:
        st.info("📌 해당 용어와 연결된 영상이 없습니다.")

    st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---")
st.caption("※ 기본 사전 + symbols_extra.json 병합 표시됨.  ingest_youtube.py 로 추가할 수 있음.")