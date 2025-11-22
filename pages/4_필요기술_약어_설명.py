# pages/4_필요기술_약어_설명.py
import streamlit as st
import json
import os
import re
from pathlib import Path
from collections import defaultdict

from PIL import Image
import numpy as np

# =========================
# 경로 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = BASE_DIR / "lib"

SYMBOLS_PATH = LIB_DIR / "symbols.json"
SYMBOLS_EXTRA_PATH = LIB_DIR / "symbols_extra.json"

CHART_IMG_ROOT = BASE_DIR / "assets" / "chart_from_excel"
CHART_MANIFEST = CHART_IMG_ROOT / "manifest.json"


# =========================
# 데이터 로드 헬퍼
# =========================
@st.cache_data(show_spinner=False)
def load_symbols():
    """symbols.json + symbols_extra.json 합쳐서 용어/약어 사전 로드"""
    def _load(p: Path):
        if not p.exists():
            return {}
        with p.open(encoding="utf-8") as f:
            return json.load(f)

    base = _load(SYMBOLS_PATH)
    extra = _load(SYMBOLS_EXTRA_PATH)

    merged = {**base, **extra}
    # 검색용 인덱스 만들기
    index = []
    for key, v in merged.items():
        aliases = set()
        aliases.add(key)
        aliases.add(v.get("name_en", ""))
        aliases.add(v.get("name_ko", ""))
        for a in v.get("aliases", []):
            aliases.add(a)

        aliases = {a.strip() for a in aliases if a and isinstance(a, str)}

        index.append(
            {
                "key": key,
                "name_en": v.get("name_en", ""),
                "name_ko": v.get("name_ko", ""),
                "aliases": sorted(aliases),
                "desc": v.get("desc_ko", ""),
            }
        )
    return index


@st.cache_data(show_spinner=False)
def load_chart_manifest():
    """엑셀에서 만든 chart_from_excel/manifest.json 로드"""
    if not CHART_MANIFEST.exists():
        return {}

    with CHART_MANIFEST.open(encoding="utf-8") as f:
        raw = json.load(f)

    # 구조를 납작하게 펴서 [ {sheet, file, abbr, name, desc, img_path}, ... ] 형태로
    items = []
    for sheet_title, info in raw.items():
        img_dir = info.get("img_dir") or ""
        img_dir_path = (CHART_IMG_ROOT / img_dir) if img_dir else CHART_IMG_ROOT
        for item in info.get("items", []):
            fname = item.get("file")
            if not fname:
                continue
            img_path = img_dir_path / fname
            items.append(
                {
                    "sheet": sheet_title,
                    "file": fname,
                    "img_path": str(img_path),
                    "abbr": item.get("abbr", ""),
                    "name": item.get("name", ""),
                    "desc": item.get("desc", ""),
                }
            )
    return items


# =========================
# 텍스트에서 약어/용어 찾기
# =========================
def find_terms_in_text(text: str, symbol_index, chart_items):
    text_l = text.lower()

    hits = []

    # 1) 뜨개 약어/용어
    for s in symbol_index:
        found_aliases = []
        for alias in s["aliases"]:
            if not alias:
                continue
            if alias.lower() in text_l:
                found_aliases.append(alias)

        if found_aliases:
            hits.append(
                {
                    "type": "symbol",
                    "label": s["key"],
                    "aliases": found_aliases,
                    "name_en": s["name_en"],
                    "name_ko": s["name_ko"],
                    "desc": s["desc"],
                }
            )

    # 2) 엑셀에서 가져온 차트 기호 이름/약어(이름에 한글이 많음)
    for ch in chart_items:
        candidates = []
        for v in [ch.get("abbr", ""), ch.get("name", "")]:
            if v and isinstance(v, str):
                candidates.append(v)
        for cand in candidates:
            if cand and cand.lower() in text_l:
                hits.append(
                    {
                        "type": "chart",
                        "label": cand,
                        "aliases": [],
                        "name_en": "",
                        "name_ko": ch.get("name", ""),
                        "desc": ch.get("desc", ""),
                        "sheet": ch.get("sheet", ""),
                        "file": ch.get("file", ""),
                        "img_path": ch.get("img_path", ""),
                    }
                )
                break

    return hits


# =========================
# 이미지 기반 차트 매칭 (픽셀 유사도)
# =========================
def load_and_prepare_image(path_or_bytes, size=(64, 64)):
    """PNG 파일 또는 업로드된 파일을 회색조/리사이즈해서 벡터로 변환"""
    if isinstance(path_or_bytes, (str, Path)):
        img = Image.open(path_or_bytes)
    else:
        img = Image.open(path_or_bytes)

    img = img.convert("L")  # grayscale
    img = img.resize(size)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr.flatten()


def match_chart_icon(uploaded_file, chart_items, top_k=5):
    """업로드한 기호 이미지와 chart_from_excel 의 PNG 들을 단순 픽셀 거리로 비교"""
    if not chart_items:
        return []

    try:
        target_vec = load_and_prepare_image(uploaded_file)
    except Exception:
        return []

    candidates = []
    for ch in chart_items:
        img_path = ch.get("img_path")
        if not img_path or not os.path.exists(img_path):
            continue
        try:
            vec = load_and_prepare_image(img_path)
        except Exception:
            continue

        # L2 거리
        dist = float(np.linalg.norm(target_vec - vec))
        candidates.append((dist, ch))

    candidates.sort(key=lambda x: x[0])
    return candidates[:top_k]


# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="필요 기술 / 약어 설명", page_icon="📘", layout="wide")
st.title("📘 필요 기술 / 약어 설명")

st.write(
    "도안 설명이나 **필요 기술 목록**을 붙여 넣으면, "
    "뜨개 약어 사전 및 차트 기호 사전에서 관련 항목을 찾아 정리해 줍니다."
)

# 데이터 미리 로드
symbol_index = load_symbols()
chart_items = load_chart_manifest()

# -------------------------
# 1) 텍스트 입력
# -------------------------
st.subheader("1️⃣ 텍스트로 기술 / 약어 찾기")

input_text = st.text_area(
    "도안 설명이나 필요 약어를 붙여 넣으세요.",
    height=200,
    placeholder="예) k2tog, ssk, YO, 중심 5코 모아뜨기, 오른코 겹쳐 3코 모아뜨기 …",
)

if st.button("🔍 텍스트에서 약어 / 차트 기호 찾기", type="primary"):
    if not input_text.strip():
        st.warning("먼저 위에 텍스트를 입력해 주세요.")
    else:
        hits = find_terms_in_text(input_text, symbol_index, chart_items)

        st.markdown("---")
        st.subheader(f"🔎 인식된 기술/약어: {len(hits)}개")

        if not hits:
            st.info("텍스트에서 인식된 약어/차트 기호가 아직 없습니다.")
        else:
            # 심플하게 타입별 묶어서 보여주기
            by_type = defaultdict(list)
            for h in hits:
                by_type[h["type"]].append(h)

            # 1) 텍스트 약어/용어
            if by_type.get("symbol"):
                st.markdown("### 🧶 뜨개 약어 / 용어")
                for h in by_type["symbol"]:
                    alias_str = ", ".join(sorted(set(h["aliases"]))) if h["aliases"] else ""
                    title = f"**{h['label']}**"
                    if h["name_en"] or h["name_ko"]:
                        title += f" — {h['name_en']} / {h['name_ko']}"
                    st.markdown(title)
                    if alias_str:
                        st.caption(f"별칭: {alias_str}")
                    if h["desc"]:
                        st.write(h["desc"])
                    st.markdown("---")

            # 2) 차트 기호
            if by_type.get("chart"):
                st.markdown("### 📊 차트 기호")
                by_sheet = defaultdict(list)
                for h in by_type["chart"]:
                    by_sheet[h.get("sheet", "기타")].append(h)

                for sheet_title in sorted(by_sheet.keys()):
                    st.markdown(f"#### 🧵 {sheet_title}")
                    for h in by_sheet[sheet_title]:
                        cols = st.columns([1, 3])
                        # 이미지
                        img_path = h.get("img_path")
                        if img_path and os.path.exists(img_path):
                            try:
                                cols[0].image(str(img_path), use_column_width=True)
                            except Exception:
                                pass
                        # 텍스트 설명
                        name = h.get("name") or h.get("label") or ""
                        cols[1].markdown(f"**{name}**")
                        if h.get("desc"):
                            cols[1].write(h["desc"])
                    st.markdown("---")

# -------------------------
# 2) 이미지로 차트 기호 찾기
# -------------------------
st.markdown("---")
st.subheader("2️⃣ 기호 이미지로 차트 기호 찾기 (이미지 매칭)")

uploaded_icon = st.file_uploader(
    "PDF나 도안에서 **차트 기호 한 칸만 잘라서** PNG / JPG 로 올려 보세요.",
    type=["png", "jpg", "jpeg"],
    key="chart_icon_upload",
)

if uploaded_icon is not None:
    st.caption("업로드한 기호 이미지")
    st.image(uploaded_icon, use_column_width=False, width=300)

    with st.spinner("차트 기호 사전에서 비슷한 기호를 찾는 중…"):
        matches = match_chart_icon(uploaded_icon, chart_items, top_k=5)

    if not matches:
        st.warning("비슷한 차트 아이콘을 찾지 못했습니다. (PNG 경로나 manifest.json 을 확인해 주세요.)")
    else:
        st.markdown("### 🔍 가장 비슷한 차트 기호 후보")
        for rank, (dist, ch) in enumerate(matches, start=1):
            cols = st.columns([1, 3])
            # 이미지
            img_path = ch.get("img_path")
            if img_path and os.path.exists(img_path):
                try:
                    cols[0].image(str(img_path), use_column_width=True)
                except Exception:
                    pass

            # 설명
            title = ch.get("name") or ch.get("abbr") or ch.get("file")
            sheet = ch.get("sheet", "")
            cols[1].markdown(f"**{rank}. {title}**")
            if sheet:
                cols[1].caption(f"소분류: {sheet}")
            if ch.get("desc"):
                cols[1].write(ch["desc"])
            cols[1].caption(f"유사도(픽셀 거리 기준): {dist:.3f}")

# -------------------------
# 하단 링크
# -------------------------
st.divider()
st.page_link("HOME.py", label="⬅️ 홈으로")