# pages/4_필요기술_약어_설명.py
import streamlit as st
import json
import os
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageOps
import numpy as np


# -----------------------------------------------------------------------------
# 경로 설정
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = BASE_DIR / "lib"
ASSETS_DIR = BASE_DIR / "assets"
CHART_EXCEL_DIR = ASSETS_DIR / "chart_from_excel"
CHART_MANIFEST_PATH = CHART_EXCEL_DIR / "manifest.json"
SYMBOLS_PATH = LIB_DIR / "symbols.json"
SYMBOLS_EXTRA_PATH = LIB_DIR / "symbols_extra.json"


# -----------------------------------------------------------------------------
# 데이터 로딩 유틸
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_symbols():
    base = {}
    extra = {}
    if SYMBOLS_PATH.exists():
        with SYMBOLS_PATH.open(encoding="utf-8") as f:
            base = json.load(f)
    if SYMBOLS_EXTRA_PATH.exists():
        try:
            with SYMBOLS_EXTRA_PATH.open(encoding="utf-8") as f:
                extra = json.load(f)
        except json.JSONDecodeError:
            extra = {}
    return {**base, **extra}


@st.cache_data(show_spinner=False)
def load_chart_manifest():
    if not CHART_MANIFEST_PATH.exists():
        return {}
    with CHART_MANIFEST_PATH.open(encoding="utf-8") as f:
        return json.load(f)


SYMBOLS = load_symbols()
CHART_MAN = load_chart_manifest()


# -----------------------------------------------------------------------------
# 이미지 특징 벡터 (간단한 유사도 기반)
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def build_icon_features():
    icons = []
    if not CHART_MAN:
        return icons

    for sheet_title, info in CHART_MAN.items():
        img_dir = info.get("img_dir", "")
        items = info.get("items", [])

        img_base = Path(img_dir)
        if not img_base.is_absolute():
            img_base = CHART_EXCEL_DIR / img_base

        for it in items:
            file = it.get("file")
            if not file:
                continue
            img_path = img_base / file
            if not img_path.exists():
                continue

            try:
                img = Image.open(img_path).convert("L")
            except:
                continue

            img_resized = ImageOps.fit(img, (64, 64))
            arr = np.asarray(img_resized, dtype="float32") / 255.0
            vec = arr.reshape(-1)
            norm = float(np.linalg.norm(vec)) or 1.0
            vec = vec / norm

            icons.append(
                {
                    "sheet": sheet_title,
                    "abbr": it.get("abbr", "").strip(),
                    "desc": it.get("desc", "").strip(),
                    "path": str(img_path.relative_to(BASE_DIR)),
                    "vec": vec,
                }
            )
    return icons


ICON_FEATURES = build_icon_features()


def find_similar_icons(upload_img, topk=5):
    if not ICON_FEATURES:
        return []

    img = upload_img.convert("L")
    img_resized = ImageOps.fit(img, (64, 64))
    vec = np.asarray(img_resized, dtype="float32").reshape(-1) / 255.0
    norm = np.linalg.norm(vec) or 1.0
    vec = vec / norm

    results = []
    for icon in ICON_FEATURES:
        score = float(np.dot(vec, icon["vec"]))
        results.append((score, icon))

    results.sort(key=lambda x: x[0], reverse=True)
    return results[:topk]


# -----------------------------------------------------------------------------
# 텍스트 약어 추출
# -----------------------------------------------------------------------------
def extract_abbr_from_text(text):
    text = text.lower()
    hits = []
    for key, v in SYMBOLS.items():
        labels = set([key, v.get("name_en", ""), v.get("name_ko", "")])
        labels.update(v.get("aliases", []))

        for label in labels:
            if label and label.lower() in text:
                hits.append(
                    {
                        "key": key,
                        "label": label,
                        "name_en": v.get("name_en", ""),
                        "name_ko": v.get("name_ko", ""),
                        "desc": v.get("desc_ko", ""),
                    }
                )
                break
    return hits


def extract_chart_names_from_text(text):
    text = text.lower()
    hits = []
    for sheet, info in CHART_MAN.items():
        for it in info.get("items", []):
            abbr = (it.get("abbr") or "").strip()
            if not abbr:
                continue
            if abbr.lower() in text:
                hits.append(
                    {"sheet": sheet, "abbr": abbr, "desc": it.get("desc", "")}
                )
    return hits


SYMBOL_NAME_LIST = sorted({k for k in SYMBOLS.keys()})
CHART_NAME_LIST = sorted(
    {it["abbr"] for _, info in CHART_MAN.items() for it in info.get("items", []) if it.get("abbr")}
)

# -----------------------------------------------------------------------------
# UI 시작
# -----------------------------------------------------------------------------
st.title("📘 필요 기술 / 약어 설명 (AI + 이미지 매칭)")

st.info(
    """
📌 **ChatGPT 프롬프트를 이용하여 도안 기호를 표준 용어로 자동 정리할 수 있습니다.**  
📌 ChatGPT 분석 결과는 다시 **1번 페이지에 붙여 넣으면 표 형식으로 정리됩니다.**
"""
)

st.divider()

# -----------------------------
# 1) 텍스트 기반 분석
# -----------------------------
raw_text = st.text_area(
    "도안 설명 / 필요한 기술 (붙여넣기)",
    placeholder="예: k2tog, 오른코 3코 교차뜨기, YO ..."
)

abbr_hits = extract_abbr_from_text(raw_text) if raw_text else []
chart_hits = extract_chart_names_from_text(raw_text) if raw_text else []

if abbr_hits or chart_hits:
    st.markdown("#### 🔍 인식된 용어 목록")

    if abbr_hits:
        st.write("**▪ 뜨개 약어 사전 기반**")
        for h in abbr_hits:
            st.write(f"- **{h['label']}** → `{h['key']}` / {h['name_ko']}")

    if chart_hits:
        st.write("**▪ 차트 기호 목록 기반**")
        for ch in chart_hits:
            st.write(f"- **{ch['abbr']}** ({ch['sheet']})")

st.divider()

# -----------------------------
# 2) 이미지로 차트 기호 인식
# -----------------------------
uploaded_icon = st.file_uploader(
    "📎 기호 이미지 업로드 (차트 도안에서 잘라낸 한 칸)",
    type=["png", "jpg", "jpeg"]
)

if uploaded_icon:
    img = Image.open(uploaded_icon)
    st.image(img, width=200)
    matches = find_similar_icons(img, topk=5)

    st.markdown("### 🔗 가장 비슷한 차트 기호")
    for score, m in matches:
        cols = st.columns([1, 2])
        with cols[0]:
            st.image(str(BASE_DIR / m["path"]), width=120)
        with cols[1]:
            st.write(f"**{m['abbr']}**  — {m['sheet']}")
            st.caption(f"유사도: {score:.3f}")

st.divider()

# -----------------------------
# 3) ChatGPT용 프롬프트 생성
# -----------------------------
st.markdown("### 🤖 ChatGPT용 프롬프트 생성")

prompt = f"""
너는 뜨개질 차트 해석 전문가야.

도안에 있는 기호를 아래의 표준 용어 중 가장 가까운 개념으로 대치해서 정리해 줘.
출력은 반드시 아래 형식:

| 도안 기호 | 표준 용어 | 설명 |
|-----------|-----------|------|

📚 표준 용어 목록:
{", ".join(SYMBOL_NAME_LIST + CHART_NAME_LIST)}

📎 내가 추가할 도안:
(여기에 이미지 업로드할게)

📌 요청:
- 이름이 다르더라도 동일 의미라면 표준 용어로 통일
- 의미 모호하면 유사한 후보 여러 개 제시
"""

st.text_area("⬇ ChatGPT에 붙여넣기", value=prompt, height=300)


### 🔘 복사 버튼 추가
st.button("📋 프롬프트 복사", on_click=lambda: st.write(
    "<script>navigator.clipboard.writeText(`" + prompt.replace("`", "\\`") + "`);</script>",
    unsafe_allow_html=True
))

st.caption("복사 후 👉 ChatGPT에 그대로 붙여넣고 도안 이미지를 업로드하세요.")