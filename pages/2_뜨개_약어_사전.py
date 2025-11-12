# pages/2_뜨개_약어_사전.py
# 상단에 추가
import json, os
from pathlib import Path
from lib import parser
import pandas as pd
import streamlit as st

BASE_PATH = "symbols.json"
EXTRA_PATH = "symbols_extra.json"   # parser.load_lib는 lib/ 아래에서 찾습니다.

# 안전 로딩 헬퍼
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

# 사용처
base = load_json_safe(BASE_PATH)
extra = load_json_safe(EXTRA_PATH)
merged = {**base, **extra}

# 병합: 기본 우선, 새 항목은 기존 키와 충돌하지 않게 ingest에서 처리됨
merged = {**base, **extra}

def first_valid_video(vlist):
    """videos 배열에서 '개별 영상' 링크(playlist가 아닌 것) 1개만 반환"""
    if not isinstance(vlist, list):
        return ""
    for v in vlist:
        url = (v.get("url") or "").strip()
        if not url:
            continue
        # playlist 전용 링크는 제외(요구사항)
        if "list=" in url and "watch?v=" not in url:
            continue
        return url
    return ""

# 표 데이터 구성
rows = []
for key, v in merged.items():
    rows.append({
        "약자(약어)": key,
        "용어(영문)": v.get("name_en",""),
        "한국어": v.get("name_ko",""),
        "설명": v.get("desc_ko",""),
        "영상": first_valid_video(v.get("videos", []))
    })
df = pd.DataFrame(rows)

# 검색/필터 UI
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

st.caption(f"총 항목: **{len(df)}** · 추가 항목(symbols_extra): **{sum(df['_is_extra'])}** · 현재 표시: **{len(fdf)}**")

# 표 렌더링(영상 하이퍼링크 1개)
st.data_editor(
    fdf[["약자(약어)","용어(영문)","한국어","설명","영상"]],
    use_container_width=True,
    hide_index=True,
    disabled=True,
    column_config={
        "영상": st.column_config.LinkColumn("영상", display_text="열기", max_chars=300)
    },
    num_rows="fixed",
    height=min(120 + len(fdf)*34, 5000),
)

st.divider()
st.caption("※ ‘lib/ingest_youtube.py’로 재생목록/단일 영상을 ingest하면 새 항목이 lib/symbols_extra.json에 누적 저장됩니다. 이 표는 기본 사전 + 추가 사전을 합쳐 보여줍니다.")