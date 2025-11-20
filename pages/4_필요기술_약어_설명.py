# pages/4_필요_기술_약어_설명.py
import json
import re
from pathlib import Path

import streamlit as st

from lib import parser
from lib.pdf_utils import extract_pdf_text   # 이미 프로젝트에 있는 유틸

# ---------------------------------------------------
# 경로 / 데이터 로드
# ---------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
CHART_MANIFEST = ROOT / "assets" / "chart_from_excel" / "manifest.json"


@st.cache_data(show_spinner=False)
def load_symbol_lib():
    """symbols.json + symbols_extra.json 합치기"""
    base = parser.load_lib("symbols.json") or {}
    extra = parser.load_lib("symbols_extra.json") or {}
    merged = {**base, **extra}
    return merged


@st.cache_data(show_spinner=False)
def load_chart_manifest():
    """엑셀에서 만든 차트 기호 매니페스트 로드"""
    if not CHART_MANIFEST.exists():
        return {}

    try:
        data = json.loads(CHART_MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    return data


@st.cache_data(show_spinner=False)
def build_indexes():
    """텍스트에서 찾기 편하게 약어/차트 기호 인덱스 구성"""

    symbols = load_symbol_lib()
    manifest = load_chart_manifest()

    # ------------ 1) 약어/기술 인덱스 ------------
    abbr_index = {}  # token(lower) -> (key, entry)

    for key, v in symbols.items():
        tokens = set()
        tokens.add(key)
        tokens.add(v.get("name_en", ""))
        tokens.add(v.get("name_ko", ""))
        for a in v.get("aliases", []):
            tokens.add(a)

        for t in tokens:
            t = (t or "").strip()
            if not t:
                continue
            abbr_index[t.lower()] = (key, v)

    # ------------ 2) 차트 기호 인덱스 ------------
    chart_items = []  # 리스트로 들고 있다가 텍스트에서 검색
    for sheet_title, info in manifest.items():
        img_dir = info.get("img_dir", "")
        for item in info.get("items", []):
            file = item.get("file", "")
            abbr = (item.get("abbr") or "").strip()
            desc = (item.get("desc") or "").strip()

            # 검색용 토큰 (이름과 설명 둘 다 사용)
            tokens = []
            if abbr:
                tokens.append(abbr)
            if desc:
                tokens.append(desc)

            if not tokens:
                continue

            chart_items.append(
                {
                    "sheet": sheet_title,
                    "img_dir": img_dir,
                    "file": file,
                    "abbr": abbr,
                    "desc": desc,
                    "tokens": tokens,
                }
            )

    return abbr_index, chart_items


def find_matches(text: str):
    """사용자가 넣은 텍스트에서 약어/차트 기호 찾기"""
    text_lower = text.lower()

    abbr_index, chart_items = build_indexes()

    # 약어 / 기술
    abbr_hits = {}  # key -> (entry, matched_tokens)
    for token, (key, entry) in abbr_index.items():
        if not token:
            continue

        # 영문/숫자는 단어 경계 사용, 한글·혼합은 그냥 포함 검사
        if re.fullmatch(r"[0-9A-Za-z+/.\-]+", token):
            pattern = r"\b" + re.escape(token) + r"\b"
            found = re.search(pattern, text_lower)
        else:
            found = token in text_lower

        if found:
            hit = abbr_hits.setdefault(key, {"entry": entry, "tokens": []})
            hit["tokens"].append(token)

    # 차트 기호 (엑셀에서 가져온 것)
    chart_hits = []
    for item in chart_items:
        found_token = None
        for token in item["tokens"]:
            t = token.lower()
            if not t:
                continue
            if t in text_lower:
                found_token = token
                break
        if found_token:
            copied = dict(item)
            copied["matched"] = found_token
            chart_hits.append(copied)

    # 정렬: 약어는 key 알파벳 순, 차트는 시트 순 + 파일명 순
    abbr_hits_sorted = sorted(abbr_hits.items(), key=lambda kv: kv[0].lower())
    chart_hits_sorted = sorted(
        chart_hits, key=lambda x: (x["sheet"], x["file"])
    )

    return abbr_hits_sorted, chart_hits_sorted


def resolve_chart_path(img_dir: str, file: str) -> Path:
    """
    manifest 안에 어떤 형태로 img_dir 이 들어가 있어도
    실제 이미지 파일 경로를 최대한 유연하게 찾아본다.
    """
    p = Path(img_dir)

    # 1) 그대로 사용 (절대 / 상대 모두 허용)
    cand = (ROOT / p) if not p.is_absolute() else p
    path1 = cand / file
    if path1.exists():
        return path1

    # 2) assets/chart_from_excel/ + img_dir
    path2 = ROOT / "assets" / "chart_from_excel" / img_dir / file
    if path2.exists():
        return path2

    # 3) img_dir의 마지막 이름만 사용
    path3 = ROOT / "assets" / "chart_from_excel" / p.name / file
    if path3.exists():
        return path3

    # 실패 시 그냥 1번 반환(어차피 존재 안 하면 Streamlit이 무시)
    return path1


# ===================================================
#  Streamlit UI
# ===================================================

st.set_page_config(page_title="필요 기술 / 약어 설명", page_icon="📘", layout="centered")

st.title("📘 필요 기술 / 약어 설명")

st.markdown(
    """
도안 설명이나 **필요 기술 목록**을 아래에 그대로 붙여 넣으면  

- 텍스트 안의 **뜨개 약어(k2tog, SSK, YO, …)** 와  
- 3페이지에서 쓰는 **차트 기호 이름(예: ‘오른코 겉켜 3코 모아뜨기’, ‘중심 5코 모아뜨기’ 등)**  

을 동시에 찾아서 정리해 줍니다.
"""
)

# ---------------------------------------------------
# 입력 영역 (텍스트 + PDF 업로드)
# ---------------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("**① 도안 텍스트 붙여넣기**")
    default_text = ""
    text = st.text_area(
        "도안에서 필요한 기술/약어를 복사해서 붙여 넣으세요.",
        value=default_text,
        height=220,
        placeholder="예) k2tog, ssk, YO, 중심 5코 모아뜨기, 오른코 겉켜 3코 모아뜨기 …",
    )

with col2:
    st.markdown("**② 또는 PDF 업로드**")
    uploaded = st.file_uploader("PDF 도안 파일", type=["pdf"], label_visibility="collapsed")
    if uploaded is not None:
        # 임시 파일로 저장 후 pdf_utils 사용
        tmp_path = ROOT / "data" / "_uploaded_tmp.pdf"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(uploaded.read())
        try:
            extracted = extract_pdf_text(str(tmp_path))
            if extracted.strip():
                # 기존 텍스트에 이어 붙이기 보다는 교체하는 쪽이 직관적
                text = extracted
                st.success("PDF에서 텍스트를 추출했어요. 아래 텍스트 상자를 확인해 주세요.")
        except Exception as e:
            st.warning(f"PDF 읽기 중 오류가 발생했습니다: {e}")

st.markdown("---")

# ---------------------------------------------------
# 분석 결과
# ---------------------------------------------------
if not text.strip():
    st.subheader("🔍 인식된 기술/약어: 0개")
    st.info("아직 텍스트가 없습니다. 위에 도안 내용을 붙여 넣거나 PDF를 업로드해 주세요.")
else:
    abbr_hits, chart_hits = find_matches(text)
    total = len(abbr_hits) + len(chart_hits)

    st.subheader(f"🔍 인식된 기술/약어: {total}개")

    # ===== 1) 텍스트 약어 / 기법 =====
    if abbr_hits:
        st.markdown("### ✳ 약어 / 텍스트 기법")

        for key, info in abbr_hits:
            entry = info["entry"]
            tokens = sorted(set(info["tokens"]))

            name_en = entry.get("name_en", "")
            name_ko = entry.get("name_ko", "")
            desc_ko = entry.get("desc_ko", "")

            st.markdown(
                f"**{key}** — {name_en} / {name_ko}"
                + (f"<br/><small>텍스트에서 발견된 표기: {', '.join(tokens)}</small>"
                   if tokens else ""),
                unsafe_allow_html=True,
            )
            if desc_ko:
                st.write(desc_ko)

            # (원하면 여기서 2페이지처럼 유튜브 썸네일/링크도 보여줄 수 있음)
            st.markdown("---")

    # ===== 2) 차트 기호 =====
    if chart_hits:
        st.markdown("### 🧵 차트 기호 (엑셀 차트 도안 기준)")

        current_sheet = None
        for item in chart_hits:
            sheet = item["sheet"]
            if sheet != current_sheet:
                st.markdown(f"#### 📂 {sheet}")
                current_sheet = sheet

            img_path = resolve_chart_path(item["img_dir"], item["file"])
            cols = st.columns([1, 3])

            # 이미지
            if img_path.exists():
                cols[0].image(str(img_path), use_column_width=True)

            # 설명
            title = item.get("abbr") or item.get("desc") or item["file"]
            desc