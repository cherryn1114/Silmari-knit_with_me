# pages/4_필요기술_약어_설명.py

import streamlit as st
import json
from pathlib import Path
from collections import defaultdict
from lib.upload_utils import uploader_with_history

from PIL import Image, ImageOps
import numpy as np
import html
import streamlit.components.v1 as components


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
    """뜨개 약어 사전(symbols.json + symbols_extra.json) 병합."""
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
    merged = {**base, **extra}
    return merged


@st.cache_data(show_spinner=False)
def load_chart_manifest():
    """엑셀에서 추출한 차트 기호 매니페스트 로드."""
    if not CHART_MANIFEST_PATH.exists():
        return {}
    with CHART_MANIFEST_PATH.open(encoding="utf-8") as f:
        manifest = json.load(f)
    return manifest


SYMBOLS = load_symbols()
CHART_MAN = load_chart_manifest()


# -----------------------------------------------------------------------------
# 차트 아이콘 이미지 feature 준비 (간단한 코사인 유사도)
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def build_icon_features():
    """chart_from_excel 아래 png들을 벡터화해서 유사도 비교에 사용."""
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
            except Exception:
                continue

            # 64x64로 맞추고 벡터화
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
                    "file": file,
                    "path": str(img_path.relative_to(BASE_DIR)),
                    "vec": vec,
                }
            )

    return icons


ICON_FEATURES = build_icon_features()


def find_similar_icons(upload_img: Image.Image, topk: int = 5):
    """업로드한 기호 이미지와 가장 비슷한 차트 아이콘 topk 반환."""
    if not ICON_FEATURES:
        return []

    img = upload_img.convert("L")
    img_resized = ImageOps.fit(img, (64, 64))
    arr = np.asarray(img_resized, dtype="float32") / 255.0
    vec = arr.reshape(-1)
    norm = float(np.linalg.norm(vec)) or 1.0
    vec = vec / norm

    scores = []
    for icon in ICON_FEATURES:
        s = float(np.dot(vec, icon["vec"]))  # cosine similarity
        scores.append((s, icon))

    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[:topk]


# -----------------------------------------------------------------------------
# 텍스트에서 약어 / 차트 기호 이름 찾기
# -----------------------------------------------------------------------------
def extract_abbr_from_text(text: str):
    """입력 텍스트에서 뜨개 약어/용어 찾기."""
    t = text.lower()
    hits = []

    for key, v in SYMBOLS.items():
        labels = set()
        labels.add(key)
        labels.add((v.get("name_en") or ""))
        labels.add((v.get("name_ko") or ""))
        for a in v.get("aliases", []):
            labels.add(a or "")

        for label in labels:
            label = label.strip()
            if not label:
                continue
            if label.lower() in t:
                hits.append(
                    {
                        "label": label,
                        "key": key,
                        "name_en": v.get("name_en", ""),
                        "name_ko": v.get("name_ko", ""),
                        "desc": v.get("desc_ko", ""),
                    }
                )
                break  # 한 번 매칭되면 그 항목은 중복 없이
    return hits


def extract_chart_names_from_text(text: str):
    """입력 텍스트에서 차트 기호 이름(엑셀상의 이름) 찾기."""
    if not CHART_MAN:
        return []

    t = text.lower()
    hits = []

    for sheet_title, info in CHART_MAN.items():
        items = info.get("items", [])
        for it in items:
            abbr = (it.get("abbr") or "").strip()
            if not abbr:
                continue
            if abbr.lower() in t:
                hits.append(
                    {
                        "sheet": sheet_title,
                        "abbr": abbr,
                        "desc": it.get("desc", ""),
                        "file": it.get("file", ""),
                    }
                )

    return hits


# 프롬프트에 넣을 이름 목록 생성
def make_symbol_name_list():
    names = set()
    for k, v in SYMBOLS.items():
        names.add(k)
        names.add(v.get("name_en", ""))
        names.add(v.get("name_ko", ""))
        for a in v.get("aliases", []):
            names.add(a)
    names = {n.strip() for n in names if n and n.strip()}
    return sorted(names)


def make_chart_name_list():
    names = set()
    for _, info in CHART_MAN.items():
        for it in info.get("items", []):
            abbr = (it.get("abbr") or "").strip()
            if not abbr:
                continue
            if abbr.startswith("__dummy__"):
                continue
            names.add(abbr)
    return sorted(names)


SYMBOL_NAME_LIST = make_symbol_name_list()
CHART_NAME_LIST = make_chart_name_list()


# -----------------------------------------------------------------------------
# Clipboard 복사 버튼 (JS)
# -----------------------------------------------------------------------------
def render_copy_button(text: str):
    """프롬프트를 클립보드에 복사하는 HTML 버튼."""
    escaped = html.escape(text)
    components.html(
        f"""
        <textarea id="prompt_to_copy" style="position:absolute; left:-10000px; top:-10000px;">{escaped}</textarea>
        <button
            onclick="
              const ta = document.getElementById('prompt_to_copy');
              ta.select();
              document.execCommand('copy');
              alert('프롬프트가 클립보드에 복사되었습니다!');
            "
            style="padding:0.4rem 0.8rem; border-radius:0.4rem; border:1px solid #ccc; cursor:pointer;"
        >
          📋 프롬프트 복사
        </button>
        """,
        height=60,
    )


# -----------------------------------------------------------------------------
# Streamlit UI 시작
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="실마리 — 필요 기술 / 약어 설명",
    page_icon="📘",
    layout="wide",
)

st.title("📘 필요 기술 / 약어 설명")

st.info(
    """
이 페이지에서는  

1. 도안 설명 텍스트에서 **필요 기술/약어**를 찾아보고,  
2. 차트 기호 **이미지로 비슷한 기호**를 찾고,  
3. ChatGPT 웹에 붙여넣어 쓸 **프롬프트를 자동 생성**할 수 있습니다.

> 💡 ChatGPT에서 표준 용어로 정리된 결과를 얻은 다음,  
> **1번 페이지(또는 2번 뜨개 약어 사전 페이지)**에 다시 붙여넣으면  
> 도안 설명을 더 깔끔하게 정리해서 쓸 수 있어요.
"""
)

st.divider()

# -----------------------------------------------------------------------------
# 1️⃣ 텍스트에서 기술/약어 찾기
# -----------------------------------------------------------------------------
st.markdown("### 1️⃣ 텍스트에서 기술/약어 찾기")

raw_text = st.text_area(
    "도안 설명 또는 필요한 기술/약어들을 아래에 붙여 넣으세요.",
    height=200,
    placeholder="예) k2tog, ssk, YO, 중심 5코 모아뜨기, 오른코 겹쳐 3코 모아뜨기 …",
)

abbr_hits = []
chart_hits = []

if raw_text.strip():
    abbr_hits = extract_abbr_from_text(raw_text)
    chart_hits = extract_chart_names_from_text(raw_text)

st.markdown("#### 🔍 인식된 기술/약어")

if not (abbr_hits or chart_hits):
    st.info("텍스트에서 인식된 약어/차트 기호가 아직 없습니다. 위에 내용을 붙여 넣어 보세요.")
else:
    if abbr_hits:
        st.markdown("##### ▪ 뜨개 약어 사전에서 찾은 항목")
        for h in abbr_hits:
            st.markdown(
                f"- **{h['label']}**  →  `{h['key']}` / {h['name_en']} / {h['name_ko']}"
            )
            if h["desc"]:
                st.caption(h["desc"])

    if chart_hits:
        st.markdown("##### ▪ 차트 기호 이름(엑셀 기준)에서 찾은 항목")
        by_sheet = defaultdict(list)
        for ch in chart_hits:
            by_sheet[ch["sheet"]].append(ch)

        for sheet_title in sorted(by_sheet.keys()):
            st.markdown(f"###### 🧵 {sheet_title}")
            for ch in by_sheet[sheet_title]:
                line = f"- **{ch['abbr']}**"
                if ch["desc"]:
                    line += f" — {ch['desc']}"
                st.markdown(line)

st.divider()

# -----------------------------------------------------------------------------
# 2️⃣ 기호 이미지로 차트 기호 찾기 (이미지 매칭)
# -----------------------------------------------------------------------------
st.markdown("### 2️⃣ 기호 이미지로 차트 기호 찾기 (이미지 매칭)")

uploaded_icon = st.file_uploader(
    "PDF나 도안에서 **차트 기호 한 칸**을 잘라서 업로드해 보세요. (PNG / JPG / JPEG)",
    type=["png", "jpg", "jpeg"],
    key="icon_uploader",
)

if uploaded_icon is not None:
    try:
        img = Image.open(uploaded_icon)
        st.markdown("**업로드한 기호 이미지**")
        st.image(img, use_column_width=False, width=260)

        if not ICON_FEATURES:
            st.warning("차트 아이콘 인덱스를 찾지 못했습니다. (manifest.json 또는 PNG 경로를 확인해 주세요.)")
        else:
            icon_matches = find_similar_icons(img, topk=6)
            if not icon_matches:
                st.info("비슷한 차트 기호를 찾지 못했습니다.")
            else:
                st.markdown("#### 🔗 비슷한 차트 기호 후보들")

                for score, icon in icon_matches:
                    cols = st.columns([1, 2])
                    with cols[0]:
                        try:
                            st.image(str(BASE_DIR / icon["path"]), use_column_width=True)
                        except Exception:
                            st.write("(이미지 로드 실패)")

                    with cols[1]:
                        title = icon["abbr"] or "(이름 없음)"
                        st.markdown(f"**{title}**")
                        st.caption(f"소분류: {icon['sheet']}")
                        if icon["desc"]:
                            st.write(icon["desc"])
                        st.caption(f"유사도 점수: {score:.3f}")

    except Exception as e:
        st.error(f"이미지 처리 중 오류가 발생했습니다: {e}")

st.divider()

# -----------------------------------------------------------------------------
# 3️⃣ ChatGPT에 직접 물어볼 때 쓸 프롬프트
# -----------------------------------------------------------------------------
st.markdown("### 3️⃣ ChatGPT에 직접 물어볼 때 쓸 프롬프트")

st.write(
    """
이 프롬프트는 **ChatGPT 웹사이트**에서 사용할 용도입니다.

1. 아래 프롬프트를 통째로 복사  
2. ChatGPT 대화창에 붙여넣기  
3. 도안 이미지(PDF/사진)를 ChatGPT에 업로드  
4. ChatGPT가 **도안에 쓰인 기호들을 표준 용어(약어)로 대치해서 표 형식으로 정리**해 줍니다.  

> 이후 ChatGPT가 정리해 준 결과를 다시 **1번 페이지/2번 페이지에 붙여넣으면**,  
> 앱 안에서 더 예쁘게 정리해서 활용할 수 있어요.
"""
)

abbr_labels = sorted({h["label"] for h in abbr_hits}) if abbr_hits else []
chart_labels = sorted({h["abbr"] for h in chart_hits}) if chart_hits else []

symbol_name_str = ", ".join(SYMBOL_NAME_LIST) if SYMBOL_NAME_LIST else "(사전 로드 실패)"
chart_name_str = ", ".join(CHART_NAME_LIST) if CHART_NAME_LIST else "(차트 사전 로드 실패)"

if raw_text.strip():
    text_snippet = raw_text.strip()
else:
    text_snippet = "(여기에 도안 설명이나, 도안에 적힌 약어/기호 설명을 추가로 붙여넣으세요.)"

prompt_lines = []

prompt_lines.append("너는 '뜨개질 차트 기호'와 '뜨개 약어'를 분석하는 전문가야.")
prompt_lines.append("")
prompt_lines.append("내가 업로드할 이미지는 **전체 뜨개 도안(차트)** 이고,")
prompt_lines.append("각 칸에 있는 표기 하나가 '기호 한 칸'이야.")
prompt_lines.append("도안 제작자마다 기호 이름과 설명이 다르기 때문에,")
prompt_lines.append("아래에 제공하는 사전을 기준으로 **표준 이름으로 정리**해 줘.")
prompt_lines.append("")
prompt_lines.append("------------------------------------------------------------")
prompt_lines.append("📚 1. 참고용 뜨개 약어 / 용어 사전")
prompt_lines.append("")
prompt_lines.append(symbol_name_str)
prompt_lines.append("")
prompt_lines.append("📚 2. 참고용 차트 기호(이미지) 이름 목록 (엑셀에서 가져온 표준 이름)")
prompt_lines.append("")
prompt_lines.append(chart_name_str)
prompt_lines.append("------------------------------------------------------------")
prompt_lines.append("")
prompt_lines.append("🧵 지금 내가 가진 도안 설명 / 텍스트는 다음과 같아:")
prompt_lines.append(text_snippet)
prompt_lines.append("")

if abbr_labels or chart_labels:
    prompt_lines.append("또, 내가 미리 찾아본 기호 후보들은 아래와 같아 (참고만 해줘):")
    if abbr_labels:
        prompt_lines.append(f"- 텍스트에서 인식된 뜨개 약어/용어: {', '.join(abbr_labels)}")
    if chart_labels:
        prompt_lines.append(f"- 텍스트에서 인식된 차트 기호 이름: {', '.join(chart_labels)}")
    prompt_lines.append("")

prompt_lines.append("------------------------------------------------------------")
prompt_lines.append("✏️ 네가 해 줄 일")
prompt_lines.append("")
prompt_lines.append("1. 내가 업로드한 도안 이미지를 보고, 사용된 기호들을 가능한 한 많이 추출해.")
prompt_lines.append("2. 각 기호를 위의 뜨개 약어/차트 기호 사전에서 **가장 가까운 표준 용어(약어)**에 매핑해.")
prompt_lines.append("3. 아래와 같은 **마크다운 표 형식**으로 정리해 줘:")
prompt_lines.append("")
prompt_lines.append("| 도안에 적힌 기호/이름 | 표준 뜨개 용어(약어) |")
prompt_lines.append("|------------------------|----------------------|")
prompt_lines.append("| (도안 표기 예시)       | (예: k2tog, 2/2 RC)  |")
prompt_lines.append("")
prompt_lines.append("4. 같은 의미의 기호가 여러 가지 이름으로 불릴 수 있으니,")
prompt_lines.append("   최대한 **중복을 줄이고, 정리된 표**를 만들어 줘.")
prompt_lines.append("")
prompt_lines.append("설명 문장은 최소한으로 유지하고,")
prompt_lines.append("가능하면 표 안에는 **'도안 표기'와 '표준 용어'**만 간단히 써 줘.")

final_prompt = "\n".join(prompt_lines)

st.text_area("📌 ChatGPT에 붙여넣을 프롬프트", value=final_prompt, height=380)

# 복사 버튼
render_copy_button(final_prompt)

st.caption(
    """
1. 위 프롬프트를 복사해서 ChatGPT에 붙여넣고, 도안 이미지를 업로드해 분석을 맡기세요.  
2. ChatGPT가 만들어 준 **표(도안 기호 → 표준 용어)**를 다시  
   👉 1번 페이지 또는 2번 '뜨개 약어 사전' 페이지에 붙여넣으면,  
   이 앱 안에서 더 정리된 형태로 계속 활용할 수 있습니다.
"""
)

st.divider()
st.page_link("HOME.py", label="⬅️ 홈으로")