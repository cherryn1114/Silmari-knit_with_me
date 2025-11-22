# pages/4_필요기술_약어_설명.py
# - 텍스트: 뜨개 약어 사전(symbols.json + symbols_extra.json)에서 약어/용어 인식
# - 텍스트: 엑셀 기반 차트 기호 이름도 함께 인식
# - 이미지: CLIP 임베딩으로 assets/chart_from_excel 의 차트 기호와 유사도 매칭

import io
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image

from lib import parser

# PDF 유틸: 프로젝트 환경에 맞춰 최대한 유연하게 import
try:
    # (예: 우리가 만든 버전)
    from lib.pdf_utils import extract_pdf_text_from_pdf as extract_pdf_text
except Exception:
    try:
        # (기존 버전 이름)
        from lib.pdf_utils import extract_pdf_text as extract_pdf_text
    except Exception:
        extract_pdf_text = None


# ---------------------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="실마리 – 필요 기술 / 약어 설명",
    page_icon="📘",
    layout="centered",
)

st.title("📘 필요 기술 / 약어 설명")

st.write(
    """
도안 설명이나 ‘필요 기술’ 목록을 아래에 그대로 붙여 넣으면  

- **뜨개 약어 사전(`lib/symbols.json` + `lib/symbols_extra.json`)** 에서 약어/용어를 찾고  
- **차트 기호 사전(`assets/chart_from_excel`의 162개 아이콘)** 과도 연결해서  

필요한 기법을 한 눈에 볼 수 있게 정리해 줍니다.  
또한 차트 기호 한 칸을 캡처한 **이미지**를 올리면,  
로컬 CLIP 임베딩으로 가장 비슷한 차트 기호를 찾아줍니다.
"""
)

BASE_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = BASE_DIR / "lib"

# ---------------------------------------------------------------------
# 1. 뜨개 약어 사전 로드 (symbols.json + symbols_extra.json)
# ---------------------------------------------------------------------
BASE = parser.load_lib("symbols.json")
try:
    EXTRA = parser.load_lib("symbols_extra.json")
except FileNotFoundError:
    EXTRA = {}
ABBR_LIB = {**BASE, **EXTRA}


def build_abbr_index():
    """
    입력 텍스트에서 약어/용어를 찾기 위한 인덱스 생성
    -> { 검색용 소문자 문자열 : (key, 원래표기) }
    """
    idx = {}
    for key, v in ABBR_LIB.items():
        candidates = set()
        candidates.add(key)
        candidates.add(v.get("name_en", ""))
        candidates.add(v.get("name_ko", ""))
        for a in v.get("aliases", []):
            candidates.add(a)

        for c in candidates:
            c = (c or "").strip()
            # 너무 짧은 키워드(k, p 등)는 오탐이 많으니 기본적으로 제외
            if len(c) < 2:
                continue
            idx[c.lower()] = (key, c)
    return idx


ABBR_INDEX = build_abbr_index()


def find_abbr_in_text(text: str):
    """텍스트 안에서 뜨개 약어/용어를 찾아내기"""
    text_l = (text or "").lower()
    hits = {}

    for token_l, (key, original) in ABBR_INDEX.items():
        if token_l in text_l:
            hits.setdefault(key, {"key": key, "names": set(), "data": ABBR_LIB[key]})
            hits[key]["names"].add(original)

    results = []
    for key, h in hits.items():
        data = h["data"]
        results.append(
            {
                "key": key,
                "name_en": data.get("name_en", ""),
                "name_ko": data.get("name_ko", ""),
                "desc": data.get("desc_ko", ""),
                "aliases": sorted(h["names"]),
            }
        )

    # 한글 이름 기준으로 정렬
    return sorted(results, key=lambda x: (x["name_ko"] or x["name_en"] or x["key"]))


# ---------------------------------------------------------------------
# 2. 엑셀에서 추출한 차트 기호 사전 로드 (assets/chart_from_excel/manifest.json)
# ---------------------------------------------------------------------
CHART_ROOT = BASE_DIR / "assets" / "chart_from_excel"
CHART_MANIFEST = CHART_ROOT / "manifest.json"


@st.cache_resource
def load_chart_manifest():
    if not CHART_MANIFEST.exists():
        return {}
    try:
        return json.loads(CHART_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return {}


def flatten_chart_icons(manifest: dict):
    """
    manifest.json 구조:
    {
      "1코 기호": {
        "sheet": "1코 기호",
        "img_dir": "1코_기호",
        "items": [
          {"file": "chart_001.png", "abbr": "겉뜨기", "desc": "..."}, ...
        ]
      },
      ...
    }

    → [ {sheet, file, img_path, name, desc}, ... ] 로 평탄화
    """
    out = []
    for sheet_title, info in manifest.items():
        img_dir_name = info.get("img_dir") or info.get("sheet") or sheet_title
        img_dir = CHART_ROOT / img_dir_name
        items = info.get("items", [])

        for item in items:
            fname = item.get("file")
            if not fname:
                continue
            abbr = (item.get("abbr") or "").strip()
            desc = (item.get("desc") or "").strip()
            img_path = img_dir / fname
            out.append(
                {
                    "sheet": sheet_title,
                    "file": fname,
                    "img_path": img_path,
                    "name": abbr or fname,
                    "desc": desc,
                }
            )
    return out


CHART_MAN = load_chart_manifest()
CHART_ICONS = flatten_chart_icons(CHART_MAN)


def build_chart_index():
    """
    텍스트에서 차트 기호 이름 찾기용 인덱스
    (엑셀의 'abbr', 'desc' 를 모두 검색 대상으로 사용)
    """
    idx = []
    for ch in CHART_ICONS:
        tokens = set()
        tokens.add(ch.get("name", ""))
        tokens.add(ch.get("desc", ""))
        for t in tokens:
            t = (t or "").strip()
            if not t:
                continue
            idx.append(
                {
                    "sheet": ch["sheet"],
                    "file": ch["file"],
                    "img_path": ch["img_path"],
                    "token": t,
                    "name": ch["name"],
                    "desc": ch["desc"],
                }
            )
    return idx


CHART_INDEX = build_chart_index()


def find_chart_in_text(text: str):
    """텍스트 안에서 차트 기호 이름(설명)을 찾아내기"""
    text_l = (text or "").lower()
    hits = []
    seen = set()

    for ch in CHART_INDEX:
        token = ch["token"]
        if not token:
            continue
        if token.lower() in text_l:
            key = (ch["sheet"], ch["file"])
            if key in seen:
                continue
            seen.add(key)
            hits.append(ch)

    # 시트 이름, 파일 이름 순 정렬
    return sorted(hits, key=lambda x: (x["sheet"], x["file"]))


# ---------------------------------------------------------------------
# 3. PDF 업로드 → 텍스트 추출
# ---------------------------------------------------------------------
st.header("1️⃣ PDF에서 텍스트 추출 (선택)")

uploaded_pdf = st.file_uploader(
    "PDF 도안 파일을 업로드하면 안에 있는 텍스트를 추출해서 아래에 넣어 줍니다.",
    type=["pdf"],
)

if "extracted_text" not in st.session_state:
    st.session_state["extracted_text"] = ""

if uploaded_pdf is not None:
    if extract_pdf_text is None:
        st.error("PDF 텍스트 추출 함수를 찾지 못했습니다. `lib/pdf_utils.py` 를 확인해 주세요.")
    else:
        try:
            data = uploaded_pdf.read()
            txt = extract_pdf_text(data)
            st.session_state["extracted_text"] = txt
            st.success("PDF에서 텍스트를 추출했습니다. 아래에서 내용을 확인/수정하세요.")
        except Exception as e:
            st.error(f"PDF 텍스트 추출 중 오류가 발생했습니다: {e}")

# ---------------------------------------------------------------------
# 4. 텍스트 직접 입력 / 수정
# ---------------------------------------------------------------------
st.header("2️⃣ 텍스트 직접 입력 / 수정")

default_text = st.session_state.get("extracted_text", "")
input_text = st.text_area(
    "도안 설명이나 ‘필요한 기술/약어’ 부분을 그대로 붙여 넣으세요.",
    value=default_text,
    height=220,
)

# ---------------------------------------------------------------------
# 텍스트에서 뜨개 약어 / 차트 이름 찾기
# ---------------------------------------------------------------------
st.subheader("🔍 텍스트 안에서 인식된 뜨개 기술 / 약어")

abbr_hits = []
chart_hits = []

if input_text.strip():
    abbr_hits = find_abbr_in_text(input_text)
    chart_hits = find_chart_in_text(input_text)

    st.caption(f"텍스트에서 인식된 **약어/기술**: {len(abbr_hits)}개")

    if abbr_hits:
        for h in abbr_hits:
            title = h["name_ko"] or h["name_en"] or h["key"]
            st.markdown(f"**{title}**  (`{h['key']}`)")
            if h["name_en"]:
                st.caption(h["name_en"])
            if h["desc"]:
                st.write(h["desc"])
            if h["aliases"]:
                alias_str = ", ".join(sorted(h["aliases"]))
                st.caption(f"텍스트에서 감지된 표기: {alias_str}")
            st.markdown("---")
    else:
        st.info("텍스트에서 인식된 약어/기술이 아직 없습니다. 다른 텍스트를 넣어 보세요.")
else:
    st.info("먼저 위 텍스트 입력란에 내용을 넣어 주세요.")

# ---------------------------------------------------------------------
# 텍스트에서 언급된 차트 기호들 (이름/설명 기반)
# ---------------------------------------------------------------------
st.subheader("🧵 텍스트 안에서 발견된 차트 기호 이름(텍스트 기반)")

if input_text.strip():
    st.caption(f"인식된 **차트 기호 이름/설명**: {len(chart_hits)}개")
    if chart_hits:
        by_sheet = defaultdict(list)
        for ch in chart_hits:
            by_sheet[ch["sheet"]].append(ch)

        for sheet_title in sorted(by_sheet.keys()):
            st.markdown(f"#### 📌 {sheet_title}")
            for ch in by_sheet[sheet_title]:
                cols = st.columns([1, 3])
                with cols[0]:
                    try:
                        if Path(ch["img_path"]).exists():
                            st.image(str(ch["img_path"]), use_column_width=True)
                    except Exception:
                        pass
                with cols[1]:
                    nm = ch["name"] or ch["file"]
                    st.markdown(f"**{nm}**")
                    if ch["desc"]:
                        st.caption(ch["desc"])
                    st.caption(f"_파일명: {ch['file']}_")
            st.markdown("---")
    else:
        st.info("텍스트에서 인식된 차트 기호 이름이 아직 없습니다.")
else:
    st.info("먼저 위 텍스트 입력란에 내용을 넣어 주세요.")

st.divider()

# ---------------------------------------------------------------------
# 5. CLIP 기반 이미지 → 차트 기호 매칭
# ---------------------------------------------------------------------
st.header("3️⃣ 기호 이미지로 차트 기호 찾기 (CLIP 임베딩 기반)")

st.write(
    """
PDF 도안에서 **차트 기호 한 칸만 캡처한 이미지**(PNG / JPG)를 업로드하면,  
`assets/chart_from_excel` 에 있는 162개의 차트 기호 이미지와  
CLIP 임베딩으로 비교해서 가장 비슷한 기호들을 찾아 줍니다.
"""
)

uploaded_img = st.file_uploader(
    "차트 기호 스크린샷 이미지를 업로드해 주세요.",
    type=["png", "jpg", "jpeg"],
    key="chart_image_uploader",
)


@st.cache_resource
def load_clip_model():
    """
    로컬 CLIP 모델 로드 (ViT-B/32)
    - torch, clip 패키지가 필요합니다.
      예) pip install torch
          pip install git+https://github.com/openai/CLIP.git
    """
    import torch
    import clip

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)
    model.eval()
    return model, preprocess, device


@st.cache_resource
def build_chart_clip_embeddings():
    """
    CHART_ICONS 의 모든 이미지를 CLIP 임베딩(정규화 벡터)으로 변환해서 캐시
    반환: (embeddings: np.ndarray[N,D], meta: list[icon_info])
    """
    if not CHART_ICONS:
        return None, []

    import torch

    model, preprocess, device = load_clip_model()

    embs = []
    meta = []
    for ch in CHART_ICONS:
        path = ch["img_path"]
        if not Path(path).exists():
            continue
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            continue

        with torch.no_grad():
            tensor = preprocess(img).unsqueeze(0).to(device)
            feat = model.encode_image(tensor)
            feat = feat / feat.norm(dim=-1, keepdim=True)
        embs.append(feat.cpu().numpy())
        meta.append(ch)

    if not embs:
        return None, []

    embs = np.vstack(embs)  # (N, D)
    return embs, meta


def find_similar_icons_clip(uploaded_file, top_k=5):
    """
    업로드된 기호 이미지와 CHART_ICONS 의 CLIP 임베딩을 비교해서
    cosine similarity 기준 top_k를 반환
    """
    if not CHART_ICONS:
        return []

    import torch

    model, preprocess, device = load_clip_model()
    embs, meta = build_chart_clip_embeddings()
    if embs is None or not len(meta):
        return []

    # 업로드 이미지 임베딩
    img = Image.open(uploaded_file).convert("RGB")
    with torch.no_grad():
        t = preprocess(img).unsqueeze(0).to(device)
        q = model.encode_image(t)
        q = q / q.norm(dim=-1, keepdim=True)
    q = q.cpu().numpy()[0]  # (D,)

    # 코사인 유사도 (이미 벡터는 정규화 되어 있으므로 dot product)
    sims = embs @ q  # (N,)
    idxs = np.argsort(-sims)[:top_k]

    results = []
    for i in idxs:
        sim = float(sims[i])
        results.append((sim, meta[i]))
    return results


if uploaded_img is not None:
    # 업로드된 원본 보여주기
    st.image(uploaded_img, caption="업로드한 기호 이미지", use_column_width=False)

    if not CHART_ICONS:
        st.warning(
            "차트 아이콘 인덱스를 찾지 못했습니다. "
            "`assets/chart_from_excel/manifest.json` 과 PNG 경로를 확인해 주세요."
        )
    else:
        with st.spinner("CLIP 임베딩으로 차트 기호 사전에서 비슷한 기호를 찾는 중…"):
            try:
                matches = find_similar_icons_clip(uploaded_img, top_k=6)
            except Exception as e:
                matches = []
                st.error(f"CLIP 기반 매칭 중 오류가 발생했습니다: {e}")

        if not matches:
            st.warning("비슷한 차트 기호를 찾지 못했습니다. 다른 이미지로 다시 시도해 보세요.")
        else:
            st.subheader("🔗 가장 비슷한 차트 기호 후보 (CLIP 기반)")
            for rank, (sim, ch) in enumerate(matches, start=1):
                cols = st.columns([1, 3])
                with cols[0]:
                    try:
                        st.image(str(ch["img_path"]), use_column_width=True)
                    except Exception:
                        pass
                with cols[1]:
                    title = ch["name"] or ch["file"]
                    st.markdown(f"**#{rank} — {title}**")
                    st.caption(f"시트: {ch['sheet']} · 파일명: {ch['file']}")
                    if ch.get("desc"):
                        st.write(ch["desc"])
                    st.caption(f"코사인 유사도: {sim:.3f}")
else:
    st.info("차트 기호 이미지를 업로드하면, CLIP 임베딩으로 가장 비슷한 기호들을 여기에서 볼 수 있습니다.")

st.divider()
st.page_link("HOME.py", label="⬅️ 홈으로")