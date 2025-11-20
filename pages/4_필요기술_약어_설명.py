# pages/4_필요기술_약어_설명.py

import json
import re
from pathlib import Path

import streamlit as st

from lib import parser
from lib.pdf_utils import extract_pdf_text_from_pdf

# ---------------------------------------------------------
# 데이터 로드: 뜨개 약어 사전 (symbols.json + symbols_extra.json)
# ---------------------------------------------------------
BASE = parser.load_lib("symbols.json") or {}
try:
    EXTRA = parser.load_lib("symbols_extra.json") or {}
except Exception:
    EXTRA = {}

SYMBOLS = {**BASE, **EXTRA}

# 약어/용어 인덱스 만들기
abbr_index = []
for key, v in SYMBOLS.items():
    name_en = v.get("name_en", "")
    name_ko = v.get("name_ko", "")
    aliases = v.get("aliases", []) or []

    # 검색에 사용할 후보 문자열들
    candidates = [key, name_en, name_ko] + aliases
    # 공백/중복 제거
    cand_clean = []
    for c in candidates:
        c = (c or "").strip()
        if not c:
            continue
        if c not in cand_clean:
            cand_clean.append(c)

    abbr_index.append(
        {
            "id": key,
            "name_en": name_en,
            "name_ko": name_ko,
            "aliases": cand_clean,
            "desc_ko": v.get("desc_ko", ""),
        }
    )

# ---------------------------------------------------------
# 데이터 로드: 차트 기호 (assets/chart_from_excel/manifest.json)
# ---------------------------------------------------------
CHART_MANIFEST_PATH = Path("assets/chart_from_excel/manifest.json")
chart_items = []

if CHART_MANIFEST_PATH.exists():
    with CHART_MANIFEST_PATH.open(encoding="utf-8") as f:
        manifest = json.load(f)

    # manifest 구조:
    # {
    #   "1코 기호": {
    #       "sheet": "1코 기호",
    #       "img_dir": "assets/chart_from_excel/1코_기호",
    #       "items": [
    #           {"file": "chart_001.png", "abbr": "겉뜨기", "desc": "..."},
    #           ...
    #       ]
    #   },
    #   ...
    # }
    for sheet_title, info in manifest.items():
        img_dir = info.get("img_dir", "")
        for item in info.get("items", []):
            chart_items.append(
                {
                    "sheet": sheet_title,
                    "file": item.get("file"),
                    "name": item.get("abbr", ""),
                    "desc": item.get("desc", ""),
                    "img_path": str(Path(img_dir) / item.get("file", "")),
                }
            )

# ---------------------------------------------------------
# 유틸 함수: 텍스트에서 약어 / 차트 이름 찾기
# ---------------------------------------------------------
def normalize(text: str) -> str:
    return (text or "").strip().lower()


def find_abbrs_in_text(text: str):
    """텍스트 안에서 뜨개 약어/용어 찾기"""
    if not text:
        return []

    text_lower = text.lower()
    hits = {}

    for item in abbr_index:
        hit = False
        for cand in item["aliases"]:
            # ASCII(영문) 약어는 소문자 비교, 한글 등은 그대로 포함 여부 확인
            if cand.isascii():
                if normalize(cand) and normalize(cand) in text_lower:
                    hit = True
                    break
            else:
                if cand and cand in text:
                    hit = True
                    break

        if hit:
            hits[item["id"]] = item

    # 한글 이름 기준으로 정렬
    return sorted(hits.values(), key=lambda x: (x["name_ko"] or x["name_en"] or x["id"]))


def find_charts_in_text(text: str):
    """텍스트 안에서 차트 기호 이름 찾기"""
    if not text:
        return []

    text_lower = text.lower()
    hits = {}

    for item in chart_items:
        name = (item["name"] or "").strip()
        if not name:
            continue

        name_lower = name.lower()
        hit = False
        # 영문/숫자만 있으면 lower 포함, 아니면 그대로 포함
        if all(ord(c) < 128 for c in name):
            if name_lower in text_lower:
                hit = True
        else:
            if name in text:
                hit = True

        if hit:
            key = f"{item['sheet']}::{item['file']}"
            hits[key] = item

    # 시트 이름 → 파일명 순 정렬
    return sorted(hits.values(), key=lambda x: (x["sheet"], x["file"] or ""))


# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
st.title("📘 필요 기술 / 약어 설명")

st.markdown(
    """
도안 설명이나 **필요 기술 목록**을 아래에 붙여 넣으면,

- 텍스트 안에 있는 **뜨개 약어 / 용어** (예: `k2tog`, `SSK`, `YO` …) 와  
- **차트 기호 이름** (예: `오른코 겹쳐 3코 모아뜨기`, `중심 5코 모아뜨기` 등)

을 한 번에 찾아서 정리해 줍니다.
"""
)

st.markdown("### 1️⃣ PDF 도안 업로드 (선택)")

uploaded_pdf = st.file_uploader("PDF 도안 파일을 선택하세요", type=["pdf"])

pdf_text = ""
if uploaded_pdf is not None:
    try:
        pdf_text = extract_pdf_text_from_pdf(uploaded_pdf)
        if pdf_text.strip():
            with st.expander("PDF에서 추출된 원문 보기", expanded=False):
                st.text_area("PDF 텍스트", value=pdf_text, height=200)
        else:
            st.info("PDF에서 읽어온 텍스트가 없습니다. 스캔본 이미지 PDF일 수 있어요.")
    except Exception as e:
        st.error(f"PDF 텍스트 추출 중 오류가 발생했습니다: {e}")

st.markdown("### 2️⃣ 텍스트 직접 입력 / 수정")

default_text = pdf_text if pdf_text else ""
user_text = st.text_area(
    "도안 설명이나 필요한 기술/약어를 붙여 넣으세요.",
    value=default_text,
    height=220,
    placeholder="예) k2tog, ssk, YO, 중심 5코 모아뜨기, 오른코 겹쳐 3코 모아뜨기 …",
)

st.markdown("---")

if not user_text.strip():
    st.subheader("🔍 인식된 기술/약어: 0개")
    st.info("텍스트에서 인식된 약어/차트 기호가 아직 없습니다. 위에 도안 내용을 붙여 넣어 보세요.")
else:
    # -----------------------------------------------------
    # 실제 인식 로직 실행
    # -----------------------------------------------------
    abbr_hits = find_abbrs_in_text(user_text)
    chart_hits = find_charts_in_text(user_text)

    total_hits = len(abbr_hits) + len(chart_hits)
    st.subheader(f"🔍 인식된 기술/약어: {total_hits}개")

    # 약어/용어 결과
    if abbr_hits:
        st.markdown("#### 🧵 뜨개 약어 / 용어")
        for item in abbr_hits:
            name_main = item["name_ko"] or item["name_en"] or item["id"]
            name_sub = item["name_en"] if item["name_ko"] else item["name_ko"]

            st.markdown(f"**• {name_main}**" + (f"  (`{item['id']}` / {name_sub})" if name_sub else f"  (`{item['id']}`)"))
            if item["desc_ko"]:
                st.write(item["desc_ko"])
            if item["aliases"]:
                alias_str = ", ".join(sorted(set(item["aliases"])))
                st.caption(f"별칭: {alias_str}")
            st.markdown("---")

    # 차트 기호 결과
    if chart_hits:
        st.markdown("#### 🗺 차트 기호")
        for ch in chart_hits:
            col_img, col_txt = st.columns([1, 2])
            with col_img:
                try:
                    col_img.image(ch["img_path"], use_column_width=True)
                except Exception:
                    col_img.write("(이미지 로드 실패)")
            with col_txt:
                title = ch["name"] or ch["file"]
                col_txt.markdown(f"**{title}**")
                col_txt.caption(f"{ch['sheet']} · {ch['file']}")
                if ch["desc"]:
                    col_txt.write(ch["desc"])
            st.markdown("---")

    if not (abbr_hits or chart_hits):
        st.info("텍스트는 읽었지만, 사전에 등록된 약어/차트 이름은 발견하지 못했습니다. 철자나 띄어쓰기를 한 번만 더 확인해 주세요 🙂")

st.divider()
st.page_link("HOME.py", label="🏠 홈으로")