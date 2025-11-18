# pages/2_뜨개_약어_사전.py

import json, os
from pathlib import Path

import pandas as pd
import streamlit as st

from lib import parser
from lib.utils import get_youtube_thumbnail   # 🔹 썸네일 함수 임포트

BASE_PATH = "symbols.json"
EXTRA_PATH = "symbols_extra.json"   # parser.load_lib는 lib/ 아래에서 찾습니다.

st.title("🧶 뜨개 약어 사전 (YouTube 썸네일 + 링크)")

# ---------------------------
# 1) 안전하게 JSON 로드
# ---------------------------
def load_json_safe(filename: str) -> dict:
    try:
        return parser.load_lib(filename)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        # 파일이 손상됐을 경우 자동 초기화
        extra_abs = Path(__file__).resolve().parent.parent / "lib" / filename
        try:
            extra_abs.write_text("{}", encoding="utf-8")
        except Exception:
            pass
        return {}

base = load_json_safe(BASE_PATH)
extra = load_json_safe(EXTRA_PATH)

# 병합: 기본 우선, 새 항목은 ingest에서 키 충돌 처리
merged = {**base, **extra}

# ---------------------------
# 2) 영상 URL에서 1개 골라오기
# ---------------------------
def first_valid_video(vlist):
    """videos 배열에서 '개별 영상' 링크(playlist가 아닌 것) 1개만 반환"""
    if not isinstance(vlist, list):
        return ""
    for v in vlist:
        url = (v.get("url") or "").strip()
        if not url:
            continue
        # 재생목록 전용 링크(영상 id 없는)는 제외
        if "list=" in url and "watch?v=" not in url and "youtu.be" not in url:
            continue
        return url
    return ""

# ---------------------------
# 3) 표 데이터 구성
# ---------------------------
rows = []
for key, v in merged.items():
    video_url = first_valid_video(v.get("videos", []))
    thumb_url = get_youtube_thumbnail(video_url) if video_url else ""

    rows.append({
        "약자(약어)": key,
        "용어(영문)": v.get("name_en",""),
        "한국어": v.get("name_ko",""),
        "설명": v.get("desc_ko",""),
        "영상": video_url,       # 클릭용 링크
        "썸네일": thumb_url,     # 이미지 URL
    })

df = pd.DataFrame(rows)

# ---------------------------
# 4) 검색/필터 UI
# ---------------------------
c1, c2, c3 = st.columns([2,1,1])
with c1:
    q = st.text_input("검색 (예: m1l / cast on / 겉뜨기 / 게이지 / 재생목록 제목 일부)", "")
with c2:
    only_new = st.checkbox("새로 추가된 항목만 보기(symbols_extra)", value=False)
with c3:
    only_with_video = st.checkbox("영상 있는 것만", value=False)

# 소스 표식
df["_is_extra"] = df["약자(약어)"].apply(lambda k: k in extra)

fdf = df.copy()
if q.strip():
    key = q.strip().lower()
    fdf = fdf[
        fdf["약자(약어)"].str.lower().str.contains(key) |
        fdf["용어(영문)"].str.lower().str.contains(key) |
        fdf["한국어"].str.lower().str.contains(key) |
        fdf["설명"].str.lower().str.contains(key)
    ]
if only_new:
    fdf = fdf[fdf["_is_extra"]]
if only_with_video:
    fdf = fdf[fdf["영상"].str.startswith("http")]

st.caption(
    f"총 항목: **{len(df)}** · "
    f"추가 항목(symbols_extra): **{sum(df['_is_extra'])}** · "
    f"현재 표시: **{len(fdf)}**"
)

# ---------------------------
# 5) 표 렌더링 (썸네일 + 링크)
# ---------------------------
st.data_editor(
    fdf[["썸네일","약자(약어)","용어(영문)","한국어","설명","영상"]],
    use_container_width=True,
    hide_index=True,
    disabled=True,
    column_config={
        # 썸네일 이미지를 작게 보여줌
        "썸네일": st.column_config.ImageColumn(
            "썸네일",
            help="YouTube 썸네일",
        ),
        # 영상은 클릭 가능한 링크
        "영상": st.column_config.LinkColumn(
            "영상 열기",
            display_text="열기",
            max_chars=300,
        ),
    },
    num_rows="fixed",
    height=min(120 + len(fdf)*34, 5000),
)

st.divider()
st.caption(
    "※ ‘lib/ingest_youtube.py’로 재생목록/단일 영상을 ingest하면 "
    "새 항목이 lib/symbols_extra.json에 누적 저장됩니다. "
    "이 표는 기본 사전 + 추가 사전을 합쳐 보여줍니다."
)