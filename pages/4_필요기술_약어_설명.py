# pages/4_필요기술_약어_설명.py

import os
import re
import json
import tempfile
from pathlib import Path
from collections import defaultdict

import streamlit as st

from lib import parser
from lib.pdf_utils import extract_pdf_text_from_pdf  # PyPDF2 기반 텍스트 추출 함수

# --------------------------------------------------------------------
# 설정 값
# --------------------------------------------------------------------
SYMBOLS_PATH = "symbols.json"
SYMBOLS_EXTRA_PATH = "symbols_extra.json"
CHART_MANIFEST_PATH = Path("assets/chart_from_excel/manifest.json")


# --------------------------------------------------------------------
# 데이터 로딩 헬퍼
# --------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_symbols() -> dict:
    """lib/symbols.json + lib/symbols_extra.json 병합."""
    try:
        base = parser.load_lib(SYMBOLS_PATH)
    except FileNotFoundError:
        base = {}
    try:
        extra = parser.load_lib(SYMBOLS_EXTRA_PATH)
    except FileNotFoundError:
        extra = {}

    merged = {**base, **extra}
    return merged


@st.cache_data(show_spinner=False)
def load_chart_manifest() -> dict:
    """assets/chart_from_excel/manifest.json 로드 (없으면 빈 dict)."""
    if not CHART_MANIFEST_PATH.exists():
        return {}
    try:
        with CHART_MANIFEST_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# --------------------------------------------------------------------
# 검색용 유틸
# --------------------------------------------------------------------
def has_korean(s: str) -> bool:
    return bool(re.search(r"[가-힣]", s or ""))


def make_symbol_patterns(key: str, v: dict) -> set:
    """약어 사전 1개 항목에서 검색에 쓸 문자열 후보들."""
    pats = set()
    pats.add(key or "")
    pats.add(v.get("name_en", ""))
    pats.add(v.get("name_ko", ""))
    for a in v.get("aliases", []) or []:
        pats.add(a)
    # 공백/빈 문자열 제거
    return {p.strip() for p in pats if isinstance(p, str) and p.strip()}


def text_contains(text: str, text_lower: str, pattern: str) -> bool:
    """영문/숫자는 단어 경계로, 한글은 단순 포함으로 검사."""
    if not pattern:
        return False

    if has_korean(pattern):
        return pattern in text
    # 영문/숫자: 소문자로 변환 후 단어 경계 검색
    p = pattern.lower()
    return bool(re.search(rf"\b{re.escape(p)}\b", text_lower))


def find_abbr_hits(text: str, symbols: dict) -> list:
    """도안 텍스트에서 약어/용어를 찾아 리스트로 반환."""
    hits = []
    text_lower = text.lower()

    for key, v in symbols.items():
        pats = make_symbol_patterns(key, v)
        matched = [p for p in pats if text_contains(text, text_lower, p)]
        if matched:
            hits.append(
                {
                    "key": key,
                    "name_en": v.get("name_en", ""),
                    "name_ko": v.get("name_ko", ""),
                    "desc": v.get("desc_ko", ""),
                    "matched": sorted(set(matched), key=len, reverse=True),
                }
            )
    # 이름 기준으로 간단 정렬
    hits.sort(key=lambda h: h["key"].lower())
    return hits


def find_chart_hits(text: str, manifest: dict) -> list:
    """도안 텍스트에서 차트 기호 이름을 찾아 리스트로 반환."""
    hits = []
    text_lower = text.lower()

    for sheet_title, sheet in manifest.items():
        items = sheet.get("items", []) or []
        for it in items:
            abbr = (it.get("abbr") or "").strip()
            desc = (it.get("desc") or "").strip()
            label = desc or abbr
            if not label:
                continue

            patterns = []
            if abbr:
                patterns.append(abbr)
            if desc:
                patterns.append(desc)

            matched = [p for p in patterns if text_contains(text, text_lower, p)]
            if matched:
                hits.append(
                    {
                        "sheet": sheet_title,
                        "file": it.get("file", ""),
                        "abbr": abbr,
                        "desc": desc,
                        "label": label,
                        "matched": sorted(set(matched), key=len, reverse=True),
                    }
                )

    # 시트명, 그 다음 label 기준 정렬
    hits.sort(key=lambda h: (h["sheet"], h["label"]))
    return hits


# --------------------------------------------------------------------
# UI 시작
# --------------------------------------------------------------------
st.set_page_config(page_title="실마리 — 필요 기술 / 약어 설명", layout="centered")
st.title("📘 필요 기술 / 약어 설명")

st.write(
    """
도안 설명이나 **필요 기술 목록 / 약어**를 아래에 그대로 붙여 넣으면  
문장 안에 있는 **영문 약어(k2tog, SSK, YO …)** 와  
**차트 기호 이름(예: ‘오른코 겹쳐 3코 모아뜨기’, ‘중심 5코 모아뜨기’ 등)** 을 동시에 찾아 정리해 줍니다.
"""
)

st.markdown("---")

# --------------------------------------------------------------------
# 1️⃣ PDF 업로드 영역
# --------------------------------------------------------------------
symbols = load_symbols()
chart_manifest = load_chart_manifest()

col_pdf, col_help = st.columns([1, 1.1])

with col_pdf:
    uploaded_pdf = st.file_uploader("1️⃣ 도안 PDF 업로드 (선택)", type=["pdf"])

with col_help:
    st.caption(
        """
- PDF를 올리면 텍스트를 추출해서 아래 입력창에 넣어 줍니다.  
- 추출된 텍스트를 직접 수정하거나, 처음부터 텍스트만 붙여 넣어도 됩니다.
"""
    )

# 세션에 텍스트 저장
if "input_text" not in st.session_state:
    st.session_state["input_text"] = ""

# PDF에서 텍스트 추출
if uploaded_pdf is not None:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_pdf.read())
            tmp_path = tmp.name

        extracted = extract_pdf_text_from_pdf(tmp_path) or ""
        # 기존 내용 뒤에 붙일지, 교체할지는 취향인데 여기서는 교체
        st.session_state["input_text"] = extracted.strip()
        st.success("PDF에서 텍스트를 추출했습니다. 아래 입력창에서 확인/수정하세요.")
    except Exception as e:
        st.error(f"PDF 텍스트 추출 중 오류가 발생했습니다: {e}")

# --------------------------------------------------------------------
# 2️⃣ 텍스트 입력 / 수정 영역
# --------------------------------------------------------------------
st.subheader("2️⃣ 텍스트 직접 입력 / 수정")
input_text = st.text_area(
    "도안 설명이나 필요할 기술/약어를 붙여 넣으세요.",
    value=st.session_state["input_text"],
    height=220,
)
st.session_state["input_text"] = input_text  # 항상 최신 값 유지

st.markdown("---")

# --------------------------------------------------------------------
# 3️⃣ 인식 결과
# --------------------------------------------------------------------
st.subheader("🔍 인식된 기술/약어")

if not input_text.strip():
    st.info("텍스트에서 인식된 약어/차트 기호가 아직 없습니다. 위에 도안 내용을 붙여 넣어 보세요.")
else:
    abbr_hits = find_abbr_hits(input_text, symbols)
    chart_hits = find_chart_hits(input_text, chart_manifest)

    total_cnt = len(abbr_hits) + len(chart_hits)
    st.caption(f"총 인식된 항목 수: **{total_cnt}개**  ·  약어/기본 기술: {len(abbr_hits)}개  ·  차트 기호: {len(chart_hits)}개")

    # 3-1. 약어 / 기본 기술
    if abbr_hits:
        st.markdown("### 🔡 약어 / 기본 기술")
        for h in abbr_hits:
            title = f"**{h['key']}** — {h['name_en']} / {h['name_ko']}"
            with st.expander(title, expanded=False):
                desc = h["desc"] or "설명 없음"
                st.write(desc)
                if h["matched"]:
                    st.caption("텍스트에서 찾은 표기: " + ", ".join(h["matched"]))
    else:
        st.info("약어/기본 기술은 인식되지 않았습니다.")

    st.markdown("---")

    # 3-2. 차트 기호 (시트별로 그룹)
    if chart_hits:
        st.markdown("### 🧵 차트 기호")
        by_sheet = defaultdict(list)
        for ch in chart_hits:
            by_sheet[ch["sheet"]].append(ch)

        for sheet_title in sorted(by_sheet.keys()):
            items = by_sheet[sheet_title]
            st.markdown(f"#### 🧶 {sheet_title} · {len(items)}개")
            for ch in items:
                label = ch["label"]
                sub = ch["abbr"] if ch["abbr"] else ch["file"]
                line = f"- **{label}**  ({sub})"
                st.markdown(line)
                if ch["matched"]:
                    st.caption("텍스트에서 찾은 표기: " + ", ".join(ch["matched"]))
    else:
        st.info("차트 기호 이름은 인식되지 않았습니다.")

st.divider()
st.page_link("HOME.py", label="⬅️ 홈으로")