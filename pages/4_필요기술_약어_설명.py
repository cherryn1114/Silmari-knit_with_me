# pages/4_필요기술_약어_설명.py
import io
import os
import json
from pathlib import Path
from collections import defaultdict

import streamlit as st
from PIL import Image
import numpy as np

from lib import parser

# --- PDF 텍스트 추출 유틸 (lib/pdf_utils 가 있으면 우선 사용) -----------------
try:
    from lib.pdf_utils import extract_pdf_text_from_pdf as extract_pdf_text  # 최신 버전
except Exception:
    try:
        from lib.pdf_utils import extract_pdf_text  # 예전 버전
    except Exception:
        # 완전한 예비용: PyPDF2 직접 사용
        try:
            import PyPDF2
        except Exception:
            PyPDF2 = None

        def extract_pdf_text(path: str) -> str:
            if PyPDF2 is None:
                return ""
            text = []
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    try:
                        t = page.extract_text() or ""
                    except Exception:
                        t = ""
                    text.append(t)
            return "\n".join(text)


# --- 전역 경로 -------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
CHART_EXCEL_DIR = ASSETS_DIR / "chart_from_excel"
CHART_MANIFEST = CHART_EXCEL_DIR / "manifest.json"

# --- 뜨개 약어 사전 로드 ----------------------------------------------------
def load_symbol_dict() -> dict:
    """symbols.json + symbols_extra.json 병합"""
    base = parser.load_lib("symbols.json") or {}
    extra = parser.load_lib("symbols_extra.json") or {}
    merged = {**base, **extra}
    return merged


SYMBOLS = load_symbol_dict()


def build_abbr_index(symbols: dict):
    """
    검색용 인덱스:
      - key 자체 (예: k2tog)
      - aliases
      - 영문/한글 이름
    """
    index = {}
    for key, v in symbols.items():
        item = {
            "key": key,
            "name_en": v.get("name_en", ""),
            "name_ko": v.get("name_ko", ""),
            "desc": v.get("desc_ko", ""),
            "aliases": v.get("aliases", []),
        }
        candidates = set()
        candidates.add(key)
        for a in v.get("aliases", []):
            candidates.add(a)
        if v.get("name_en"):
            candidates.add(v["name_en"])
        if v.get("name_ko"):
            candidates.add(v["name_ko"])
        for c in candidates:
            c2 = c.strip()
            if not c2:
                continue
            index[c2.lower()] = item
    return index


ABBR_INDEX = build_abbr_index(SYMBOLS)


def find_abbrs_in_text(text: str):
    """
    아주 단순한 방식:
    - 소문자로 바꾸고
    - 인덱스에 있는 용어가 부분 문자열로 들어가는지 확인
    """
    hits = {}
    lower = text.lower()
    for token, item in ABBR_INDEX.items():
        if token and token in lower:
            key = item["key"]
            if key in hits:
                continue
            hits[key] = item
    # 표시용 리스트로 정리
    out = []
    for key, item in hits.items():
        out.append(
            {
                "key": key,
                "name_en": item["name_en"],
                "name_ko": item["name_ko"],
                "desc": item["desc"],
            }
        )
    return out


# --- 차트 기호(엑셀에서 가져온 162개 아이콘) 인덱스 --------------------------
def load_chart_manifest():
    if not CHART_MANIFEST.exists():
        return {}
    try:
        with CHART_MANIFEST.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


CHART_MAN = load_chart_manifest()


def build_chart_icon_index(manifest: dict):
    """
    manifest.json 을 평탄화해서
    [
      {sheet, file, path, abbr, desc},
      ...
    ] 형태로 만듦
    """
    icons = []
    root = CHART_EXCEL_DIR

    for sheet_title, info in manifest.items():
        img_dir = info.get("img_dir", "")
        if img_dir:
            sheet_dir = root / img_dir
        else:
            sheet_dir = root

        for it in info.get("items", []):
            fname = it.get("file")
            if not fname:
                continue
            path = sheet_dir / fname
            if not path.exists():
                continue
            icons.append(
                {
                    "sheet": sheet_title,
                    "file": fname,
                    "path": path,
                    "abbr": it.get("abbr", ""),
                    "desc": it.get("desc", ""),
                }
            )
    return icons


CHART_ICONS = build_chart_icon_index(CHART_MAN)


# 아이콘 이미지 캐시 (성능용)
@st.cache_data(show_spinner=False)
def load_icon_arrays():
    arrs = []
    for icon in CHART_ICONS:
        try:
            img = Image.open(icon["path"]).convert("L").resize((64, 64))
            arr = np.asarray(img, dtype=np.float32) / 255.0
            arrs.append(arr)
        except Exception:
            arrs.append(None)
    return arrs


ICON_ARRAYS = load_icon_arrays()


def find_similar_icons(upload_img: Image.Image, topk: int = 5):
    """
    업로드된 한 칸짜리 차트 기호 이미지를,
    assets/chart_from_excel 에 있는 아이콘들과 비교해서
    MSE(평균제곱오차)가 작은 순으로 topk 반환.
    """
    if not CHART_ICONS:
        return []

    # 업로드 이미지 전처리
    img = upload_img.convert("L").resize((64, 64))
    base = np.asarray(img, dtype=np.float32) / 255.0

    scores = []
    for icon, ref_arr in zip(CHART_ICONS, ICON_ARRAYS):
        if ref_arr is None:
            continue
        mse = float(((base - ref_arr) ** 2).mean())
        scores.append((mse, icon))

    scores.sort(key=lambda x: x[0])
    return scores[:topk]


# --- ChatGPT 프롬프트 생성 -----------------------------------------------
def build_prompt(user_text: str, abbr_hits: list, icon_hits: list):
    """
    사용자가 입력한 도안/범례 텍스트, 앱이 인식한 약어와
    (선택) 차트 기호 후보들을 이용해서
    ChatGPT 에 붙여넣을 프롬프트를 만들어 준다.
    """
    # 약어/기호 사전을 프롬프트 안에 같이 넣어 줄 리스트
    abbr_lines = []
    for key, v in SYMBOLS.items():
        line = f"- {key} : {v.get('name_en','')} / {v.get('name_ko','')}"
        if v.get("desc_ko"):
            line += f" — {v['desc_ko']}"
        abbr_lines.append(line)
    abbr_block = "\n".join(sorted(abbr_lines))

    chart_lines = []
    # CHART_MAN 구조를 그대로 사용
    for sheet_title, info in CHART_MAN.items():
        for it in info.get("items", []):
            ab = it.get("abbr", "")
            desc = it.get("desc", "")
            if not ab and not desc:
                continue
            label = ab or desc
            if ab and desc:
                line = f"- {label} ({sheet_title}) — {desc}"
            else:
                line = f"- {label} ({sheet_title})"
            chart_lines.append(line)
    chart_block = "\n".join(chart_lines)

    # 우리가 이미 인식해 준 항목들 (참고용)
    detected_lines = []
    if abbr_hits:
        detected_lines.append("● 이 앱이 텍스트에서 미리 찾아낸 뜨개 약어:")
        for h in abbr_hits:
            line = f"- {h['key']} : {h.get('name_en','')} / {h.get('name_ko','')}"
            detected_lines.append(line)
    if icon_hits:
        detected_lines.append("\n● 이 앱이 이미지 매칭으로 추정한 차트 기호 후보:")
        for score, icon in icon_hits:
            label = icon.get("abbr") or icon.get("desc") or icon["file"]
            line = f"- {label} (시트: {icon['sheet']}, 파일: {icon['file']}, MSE={score:.3f})"
            detected_lines.append(line)

    detected_block = "\n".join(detected_lines) if detected_lines else "(앱에서 미리 인식한 항목은 없습니다.)"

    prompt = f"""너는 뜨개질 차트 도안과 약어 설명을 분석하는 전문가야.

내가 곧 올릴 이미지는 뜨개 도안(차트)이고, 아래에 붙여넣는 텍스트는 그 도안에 적힌 기호 설명/필요 기술/약어 설명이야.
이 도안에서 쓰인 기호 이름들은 출판사/디자이너마다 다르기 때문에, 너는 가능한 한
아래에 제공하는 "표준 뜨개 약어 사전" 과 "표준 차트 기호 사전"에 있는 용어들로 **매칭/대치**해서 정리해 줘.

[1] 도안에서 복사한 원본 텍스트 (범례/필요 기술 설명)
--------------------------------
{user_text.strip() or "(사용자가 아직 텍스트를 붙여넣지 않았음)"}
--------------------------------

[2] 이 앱이 미리 인식한 용어 (참고용)
--------------------------------
{detected_block}
--------------------------------

[3] 참고용 표준 뜨개 약어 사전
(가능하면 이 목록 안에서 가장 가까운 것을 골라서 매칭해 줘)
--------------------------------
{abbr_block}
--------------------------------

[4] 참고용 표준 차트 기호 사전 (엑셀에서 가져온 162종)
(이 목록의 이름을 기준으로 도안의 기호 설명을 최대한 매칭해 줘)
--------------------------------
{chart_block}
--------------------------------

너의 작업:
1. [1]의 원본 텍스트를 문장 단위/기호 단위로 나누어서 목록으로 만들어라.
2. 각 항목마다, [3] 또는 [4]의 표준 용어 중에서 의미가 가장 비슷한 것을 찾아서 매칭해라.
3. 만약 정확히 일치하는 표준 용어가 없으면, "새 용어"라고 표시하고, 어떤 동작인지 한글로 짧게 요약 설명해라.
4. 최종 결과는 아래 형식의 표로 정리해라.

- 원본 기호 이름/설명:
- 추정 표준 약어(있다면):
- 추정 표준 차트 기호 이름(있다면):
- 동작 요약 설명(한국어, 초보자도 이해할 수 있게):

가능하면 최대한 구체적으로, 하지만 표 형태로 깔끔하게 정리해 줘."""
    return prompt


# --------------------------------------------------------------------------
# Streamlit UI 시작
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="실마리 — 필요 기술 / 약어 설명",
    page_icon="📘",
    layout="centered",
)

st.title("📘 필요 기술 / 약어 설명")

st.markdown(
    """
도안의 **필요 기술·약어 설명**을 정리하고,  
마지막에는 ChatGPT에 그대로 붙여넣을 수 있는 **프롬프트**도 자동으로 만들어줍니다.

1. PDF 도안이나 텍스트를 붙여넣어 약어를 인식하고  
2. (선택) 차트 기호 한 칸 이미지를 올려 비슷한 기호 후보를 보고  
3. 아래에서 생성된 프롬프트를 ChatGPT에 복사해서 사용하면 됩니다.
"""
)

# --------------------------------------------------------------------------
# 1. PDF 업로드 → 텍스트 추출
# --------------------------------------------------------------------------
st.header("1️⃣ 도안 PDF / 이미지에서 텍스트 가져오기 (선택)")

uploaded_pdf = st.file_uploader(
    "도안 PDF 파일을 업로드하면 텍스트를 최대한 추출해 줍니다. (텍스트가 잘 안 나올 수도 있어요)",
    type=["pdf"],
    key="pdf_uploader",
)

if uploaded_pdf is not None:
    tmp_path = BASE_DIR / "_tmp_uploaded.pdf"
    with open(tmp_path, "wb") as f:
        f.write(uploaded_pdf.read())

    with st.spinner("PDF에서 텍스트를 추출하는 중입니다…"):
        raw_text = extract_pdf_text(str(tmp_path)) or ""
    tmp_path.unlink(missing_ok=True)

    if raw_text.strip():
        st.success("PDF에서 텍스트를 추출했습니다. 아래 2번 영역의 텍스트에 복사해 넣어 사용하세요.")
        st.text_area("추출된 원본 텍스트 (읽기전용)", raw_text, height=200, key="pdf_text", disabled=True)
    else:
        st.error("텍스트를 거의 추출하지 못했습니다. 스캔 이미지 PDF일 수 있어요. 직접 텍스트를 타이핑해 주세요.")


# --------------------------------------------------------------------------
# 2. 텍스트 직접 입력 / 수정
# --------------------------------------------------------------------------
st.header("2️⃣ 텍스트 직접 입력 / 수정")

default_example = "예) k2tog, ssk, YO, 중심 5코 모아뜨기, 오른코 겹쳐 3코 모아뜨기 …"
user_text = st.text_area(
    "도안 설명이나 필요할 기술/약어를 여기에 붙여 넣으세요.",
    value="",
    placeholder=default_example,
    height=200,
    key="user_text_area",
)

abbr_hits = []
if user_text.strip():
    abbr_hits = find_abbrs_in_text(user_text)
    st.markdown("---")
    st.subheader(f"🔍 인식된 기술/약어: {len(abbr_hits)}개")

    if abbr_hits:
        for h in sorted(abbr_hits, key=lambda x: x["key"].lower()):
            st.markdown(
                f"- **{h['key']}** — {h.get('name_en','')} / {h.get('name_ko','')}"
                + (f"<br/>{h['desc']}" if h.get("desc") else ""),
                unsafe_allow_html=True,
            )
    else:
        st.info("텍스트에서 인식된 약어/차트 기호가 아직 없습니다. 더 많은 내용을 붙여 넣어 보세요.")
else:
    st.info("위 텍스트 칸에 도안의 필요 기술/범례 설명을 붙여 넣으면, 여기에서 뜨개 약어를 찾아줍니다.")

# --------------------------------------------------------------------------
# 3. (선택) 기호 이미지로 차트 기호 후보 찾기
# --------------------------------------------------------------------------
st.header("3️⃣ 기호 이미지로 차트 기호 후보 찾기 (선택)")

st.caption(
    """
차트 기호 한 칸만 **잘라서 스크린샷**으로 업로드하면,  
엑셀에서 가져온 162개 차트 기호 중에서 **가장 비슷한 기호 후보**를 찾아줍니다.
(지금은 전체 차트보다는 한 칸짜리 아이콘을 올릴 때 더 잘 맞아요.)
"""
)

uploaded_icon = st.file_uploader(
    "차트 기호 한 칸 스크린샷 업로드 (PNG/JPG)",
    type=["png", "jpg", "jpeg"],
    key="icon_uploader",
)

chart_hits = []
if uploaded_icon is not None:
    try:
        img = Image.open(uploaded_icon)
        st.image(img, caption="업로드한 기호 이미지", use_column_width=False)
        with st.spinner("차트 기호 라이브러리와 비교 중…"):
            chart_hits = find_similar_icons(img, topk=5)
        if not chart_hits:
            st.warning("차트 아이콘 인덱스를 찾지 못했습니다. (manifest.json 또는 PNG 경로를 확인하세요.)")
        else:
            st.subheader("🧵 가장 비슷한 차트 기호 후보들")
            for rank, (score, icon) in enumerate(chart_hits, start=1):
                cols = st.columns([1, 2])
                with cols[0]:
                    try:
                        icon_img = Image.open(icon["path"])
                        st.image(icon_img, use_column_width=True)
                    except Exception:
                        st.write("(이미지 로드 실패)")
                with cols[1]:
                    label = icon.get("abbr") or icon.get("desc") or icon["file"]
                    st.markdown(f"**#{rank}. {label}**")
                    st.caption(
                        f"시트: {icon['sheet']} · 파일: {icon['file']} · MSE={score:.3f}"
                    )
    except Exception as ex:
        st.error(f"이미지 처리 중 오류가 발생했습니다: {ex}")

# --------------------------------------------------------------------------
# 4. ChatGPT에 직접 물어볼 때 쓸 프롬프트
# --------------------------------------------------------------------------
st.header("💬 ChatGPT에 직접 물어볼 때 쓸 프롬프트")

st.markdown(
    """
아래 버튼을 누르면,  
위에서 입력한 텍스트와 이 앱이 알고 있는 **뜨개 약어/차트 기호 사전**을 한 번에 포함한 프롬프트를 만들어 줍니다.

이 프롬프트를 **ChatGPT 대화창에 그대로 복사한 다음**,  
같은 차트 이미지를 함께 업로드해서 “이 도안의 기호 설명을 표준 용어로 정리해 줘” 라고 요청하면 됩니다.
"""
)

if st.button("🧶 ChatGPT용 프롬프트 만들기"):
    prompt_text = build_prompt(user_text, abbr_hits, [h for h in chart_hits] if chart_hits else [])
    st.success("프롬프트를 생성했습니다. 아래 내용을 복사해서 ChatGPT에 붙여 넣으세요.")
    st.text_area(
        "복사해서 ChatGPT에 붙여넣을 프롬프트",
        value=prompt_text,
        height=400,
        key="gpt_prompt_area",
    )

st.divider()
st.page_link("HOME.py", label="🏠 홈으로")