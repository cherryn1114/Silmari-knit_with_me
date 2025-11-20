# pages/4_필요기술_약어_설명.py
# 📘 필요 기술 / 약어 설명 + 기호 이미지 매칭

from __future__ import annotations
import io
import json
import re
from collections import defaultdict
from pathlib import Path

import streamlit as st
from PIL import Image

from lib.pdf_utils import extract_pdf_text_from_pdf
from lib import parser  # symbols.json / symbols_extra.json 로드용

# -------------------------------------------------------------------
# 경로 설정
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = BASE_DIR / "lib"

SYMBOLS_PATH = LIB_DIR / "symbols.json"
SYMBOLS_EXTRA_PATH = LIB_DIR / "symbols_extra.json"

CHART_ROOT = BASE_DIR / "assets" / "chart_from_excel"
CHART_MANIFEST = CHART_ROOT / "manifest.json"


# -------------------------------------------------------------------
# 1. 뜨개 약어 / 용어 사전 로드
# -------------------------------------------------------------------
@st.cache_resource
def load_knit_symbols() -> dict:
    base = parser.load_lib("symbols.json") or {}
    extra = parser.load_lib("symbols_extra.json") or {}
    merged = {**base, **extra}
    return merged


@st.cache_resource
def build_abbr_index():
    """
    약어/별칭/이름 등으로 검색할 수 있도록 인덱스를 만든다.
    """
    lib = load_knit_symbols()
    idx = {}

    def add_key(k: str, entry_key: str):
        k = (k or "").strip()
        if not k:
            return
        idx.setdefault(k.lower(), set()).add(entry_key)

    for key, v in lib.items():
        add_key(key, key)
        add_key(v.get("name_en", ""), key)
        add_key(v.get("name_ko", ""), key)
        for a in v.get("aliases", []):
            add_key(a, key)

    return lib, idx


# -------------------------------------------------------------------
# 2. 차트 아이콘(엑셀에서 뽑은 PNG) 인덱스 + 이미지 특징 벡터
# -------------------------------------------------------------------
def _img_to_feature_vec(img: Image.Image, size: int = 32) -> list[int]:
    """
    아주 단순한 '퍼셉추얼 해시' 비슷한 특징 벡터
    - 흑백 변환 후 size x size 로 리사이즈
    - 평균보다 밝으면 1, 아니면 0
    """
    g = img.convert("L").resize((size, size))
    data = list(g.getdata())
    if not data:
        return [0] * (size * size)
    mean = sum(data) / len(data)
    return [1 if px > mean else 0 for px in data]


def _hamming(a: list[int], b: list[int]) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


@st.cache_resource
def load_chart_icon_index():
    """
    assets/chart_from_excel/manifest.json + PNG 파일들을 읽어서
    이미지 검색용 인덱스를 만든다.
    반환값: [{sheet, abbr, desc, img_path, vec}, ...]
    """
    if not CHART_MANIFEST.exists():
        return []

    with CHART_MANIFEST.open(encoding="utf-8") as f:
        manifest = json.load(f)

    items = []
    for sheet_title, info in manifest.items():
        img_dir = CHART_ROOT / info["img_dir"]
        for it in info["items"]:
            fname = it["file"]
            abbr = it.get("abbr", "")
            desc = it.get("desc", "")
            img_path = img_dir / fname
            if not img_path.exists():
                continue
            try:
                img = Image.open(img_path)
                vec = _img_to_feature_vec(img)
            except Exception:
                continue

            items.append(
                {
                    "sheet": sheet_title,
                    "abbr": abbr,
                    "desc": desc,
                    "img_path": img_path,
                    "vec": vec,
                }
            )
    return items


def find_similar_chart_icons(query_img: Image.Image, topk: int = 5):
    """
    업로드한 기호 이미지를 기준으로 chart_from_excel 아이콘들 중
    가장 비슷한 것들을 반환.
    """
    q_vec = _img_to_feature_vec(query_img)
    index = load_chart_icon_index()
    if not index:
        return []

    scored = []
    for it in index:
        d = _hamming(q_vec, it["vec"])
        scored.append((d, it))

    scored.sort(key=lambda x: x[0])
    return scored[:topk]


# -------------------------------------------------------------------
# 3. 텍스트에서 약어/차트 이름 찾기
# -------------------------------------------------------------------
def normalize_token(t: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣+/]", "", t or "").strip().lower()


def analyze_text(text: str):
    """
    입력 텍스트에서:
      - 뜨개 약어/용어 (symbols.json + symbols_extra.json)
      - 차트 이름(Chart Name.xlsx에서 온 abbr/desc)
    을 찾아 리스트로 반환.
    """
    lib, abbr_index = build_abbr_index()
    chart_index = load_chart_icon_index()

    # 1) 약어/용어 토큰 매칭 (k2tog, ssk, 겉뜨기, …)
    tokens = [normalize_token(t) for t in re.split(r"[\s,;()]+", text)]
    tokens = [t for t in tokens if t]

    abbr_hits = {}
    for t in tokens:
        hits = abbr_index.get(t.lower())
        if not hits:
            continue
        for key in hits:
            abbr_hits.setdefault(key, {"count": 0})
            abbr_hits[key]["count"] += 1

    abbr_results = []
    for key, info in abbr_hits.items():
        v = lib[key]
        abbr_results.append(
            {
                "key": key,
                "name_en": v.get("name_en", ""),
                "name_ko": v.get("name_ko", ""),
                "count": info["count"],
                "desc": v.get("desc_ko", ""),
            }
        )

    # 2) 차트 이름(한글 설명 등) 부분 문자열 검색
    chart_results = []
    if chart_index:
        for it in chart_index:
            name = (it["abbr"] or "").strip()
            desc = (it["desc"] or "").strip()
            if not name and not desc:
                continue

            found = False
            if name and name in text:
                found = True
            elif desc and desc in text:
                found = True

            if found:
                chart_results.append(
                    {
                        "sheet": it["sheet"],
                        "name": name or desc,
                        "desc": desc,
                        "img_path": it["img_path"],
                    }
                )

    return abbr_results, chart_results


# -------------------------------------------------------------------
# 4. Streamlit UI
# -------------------------------------------------------------------
st.set_page_config(page_title="실마리 — 필요 기술 / 약어 설명", page_icon="📘", layout="wide")

st.title("📘 필요 기술 / 약어 설명")

st.write(
    "도안 설명이나 **필요 기술 목록**을 붙여 넣으면, "
    "문장 안에 있는 **약어(k2tog, SSK, YO …)** 와 "
    "**차트 기호 이름(예: ‘오른코 겹쳐 3코 모아뜨기’ 등)** 을 한 번에 찾아 정리해 줍니다."
)

st.markdown("---")

# -------------------------------------------------------------------
# (A) PDF 업로드 → 텍스트 추출
# -------------------------------------------------------------------
st.subheader("1️⃣ PDF에서 텍스트 가져오기 (선택사항)")

uploaded_pdf = st.file_uploader(
    "도안 PDF를 올리면 텍스트를 최대한 추출해서 아래 입력창에 넣어 줍니다.",
    type=["pdf"],
    accept_multiple_files=False,
    key="pdf_uploader",
)

if uploaded_pdf is not None:
    # Temporary file로 저장 후 처리
    tmp_path = Path("tmp_uploaded.pdf")
    with tmp_path.open("wb") as f:
        f.write(uploaded_pdf.getbuffer())

    with st.spinner("PDF에서 텍스트를 추출하는 중입니다…"):
        extracted = extract_pdf_text_from_pdf(tmp_path)
    tmp_path.unlink(missing_ok=True)

    if extracted.strip():
        st.success("PDF에서 텍스트를 추출했습니다. 아래 입력창에서 확인/수정하세요.")
        # 기존 입력값과 합치지 않고, 이번에 가져온 텍스트로 교체
        st.session_state["input_text"] = extracted
    else:
        st.warning("PDF에서 의미 있는 텍스트를 거의 찾지 못했습니다. (차트/이미지 위주 도안일 수 있어요.)")

# -------------------------------------------------------------------
# (B) 텍스트 직접 입력 / 수정
# -------------------------------------------------------------------
st.subheader("2️⃣ 텍스트 직접 입력 / 수정")

default_text = st.session_state.get("input_text", "")
input_text = st.text_area(
    "도안 설명이나 필요한 기술/약어를 붙여 넣으세요.",
    value=default_text,
    height=200,
)

# -------------------------------------------------------------------
# (C) 텍스트 분석: 약어 + 차트 이름
# -------------------------------------------------------------------
st.markdown("---")
st.subheader("🔍 인식된 기술/약어 (텍스트 기준)")

if input_text.strip():
    abbr_hits, chart_hits = analyze_text(input_text)

    total_cnt = len(abbr_hits) + len(chart_hits)
    st.caption(f"텍스트에서 찾은 항목 수: **{total_cnt}개** "
               f"(약어/용어 {len(abbr_hits)}개, 차트 기호 이름 {len(chart_hits)}개)")

    if abbr_hits:
        st.markdown("#### 🧶 뜨개 약어 / 용어")
        for h in abbr_hits:
            st.markdown(
                f"- **{h['key']}** — {h['name_en']} / {h['name_ko']}  "
                f"  - 사용 횟수: {h['count']}회  "
            )
            if h["desc"]:
                st.caption(h["desc"])

    if chart_hits:
        st.markdown("#### 🧵 텍스트로 찾은 차트 기호")
        by_sheet = defaultdict(list)
        for ch in chart_hits:
            by_sheet[ch["sheet"]].append(ch)

        for sheet_title in sorted(by_sheet.keys()):
            st.markdown(f"##### 📂 {sheet_title}")
            for ch in by_sheet[sheet_title]:
                cols = st.columns([1, 3])
                with cols[0]:
                    try:
                        st.image(str(ch["img_path"]), use_container_width=True)
                    except Exception:
                        st.write("이미지 로드 실패")
                with cols[1]:
                    title = ch["name"] or "(이름 없음)"
                    st.markdown(f"**{title}**")
                    if ch["desc"]:
                        st.caption(ch["desc"])
            st.markdown("---")
else:
    st.info("아직 텍스트를 입력하지 않았습니다. 위에 도안 내용을 붙여 넣어 보세요.")


# -------------------------------------------------------------------
# (D) 이미지로 기호 찾기 (업로드한 기호 한 장 기준)
# -------------------------------------------------------------------
st.markdown("---")
st.subheader("3️⃣ 기호 이미지로 차트 기호 찾기 (이미지 매칭)")

st.write(
    "PDF나 도안에서 **기호 한 칸만 스크린샷** 해서 올리면, "
    "차트 기호 사전(엑셀에서 가져온 162개) 중에서 가장 비슷한 기호들을 찾아 보여줍니다."
)

uploaded_img = st.file_uploader(
    "차트 기호 스크린샷(이미지)을 업로드하세요. (PNG / JPG)",
    type=["png", "jpg", "jpeg"],
    key="chart_symbol_image",
)

if uploaded_img is not None:
    try:
        img = Image.open(io.BytesIO(uploaded_img.getbuffer()))
        st.image(img, caption="업로드한 기호 이미지", use_container_width=False)
    except Exception as e:
        st.error(f"이미지 열기 실패: {e}")
        img = None

    if img is not None:
        with st.spinner("차트 기호 사전에서 비슷한 기호를 찾는 중입니다…"):
            matches = find_similar_chart_icons(img, topk=8)

        if not matches:
            st.warning("차트 아이콘 인덱스를 찾지 못했습니다. (manifest.json 또는 PNG 경로를 확인해 주세요.)")
        else:
            st.markdown("#### 🔗 가장 비슷한 차트 기호 후보")
            cols_per_row = 4
            for i, (dist, it) in enumerate(matches, start=1):
                if (i - 1) % cols_per_row == 0:
                    row = st.columns(cols_per_row)
                col = row[(i - 1) % cols_per_row]

                with col:
                    try:
                        col.image(str(it["img_path"]), use_container_width=True)
                    except Exception:
                        col.write("이미지 로드 실패")

                    name = it["abbr"] or it["desc"] or "(이름 없음)"
                    col.markdown(f"**{name}**")
                    col.caption(f"{it['sheet']} · 거리 {dist}")

st.divider()
st.page_link("HOME.py", label="⬅️ 홈으로")