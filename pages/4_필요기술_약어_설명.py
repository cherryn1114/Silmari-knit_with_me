# pages/4_필요기술_약어_설명.py
import re
import json
from pathlib import Path

import streamlit as st
from lib import parser, abbr_extract

# -----------------------------
# 공통 설정
# -----------------------------
st.set_page_config(
    page_title="실마리 — 필요 기술 / 약어 설명",
    page_icon="📘",
    layout="wide",
)

ROOT = Path(__file__).resolve().parent.parent

# -----------------------------
# 1) 뜨개 약어 사전 로드 (symbols + symbols_extra)
# -----------------------------
base = parser.load_lib("symbols.json")
extra = parser.load_lib("symbols_extra.json")
symbols = {**base, **extra}  # 기본 + 내가 추가한 것

# -----------------------------
# 2) 차트 기호 매니페스트 로드 (엑셀 → 이미지)
# -----------------------------
MANIFEST_PATH = ROOT / "assets" / "chart_from_excel" / "manifest.json"
try:
    chart_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
except FileNotFoundError:
    chart_manifest = {}

# 차트 이름 정리 함수 (3페이지에서 쓴 것과 동일)
def clean_chart_name(raw: str) -> str:
    """
    'chart_001.png (겉뜨기)' -> '겉뜨기'
    'chart_022.png(M1R)'    -> 'M1R'
    """
    if not raw:
        return ""
    s = re.sub(r"chart_\d+\.png\s*", "", raw).strip()
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    return s


# -----------------------------
# 3) 통합 인덱스 만들기
#    key 문자열 -> 정보(dict)
# -----------------------------
index: dict[str, dict] = {}

# (a) 약어/용어 사전
for key, v in symbols.items():
    entry = {
        "kind": "abbr",  # 약어/텍스트
        "key": key,
        "name_en": v.get("name_en", ""),
        "name_ko": v.get("name_ko", ""),
        "desc_ko": v.get("desc_ko", ""),
        "image": None,
    }

    def add_label(s: str):
        s = (s or "").strip()
        if not s:
            return
        index.setdefault(s, entry)

    add_label(key)
    add_label(v.get("name_en", ""))
    add_label(v.get("name_ko", ""))
    for a in v.get("aliases", []):
        add_label(a)

# (b) 차트 기호 인덱스
for sheet_title, sheet in chart_manifest.items():
    img_dir = ROOT / sheet["img_dir"]
    for item in sheet["items"]:
        raw_abbr = (item.get("abbr", "") or "").strip()
        name = clean_chart_name(raw_abbr)
        desc = (item.get("desc", "") or "").strip()
        file_name = item.get("file", "")
        img_path = img_dir / file_name

        if not name:
            # 이름이 없으면 파일명으로라도 등록
            name = file_name

        entry = {
            "kind": "chart",
            "sheet": sheet_title,
            "key": name,
            "name_en": "",
            "name_ko": name,
            "desc_ko": desc,
            "image": str(img_path) if img_path.exists() else None,
        }

        # 이름 / 설명 / 파일명을 모두 검색 키로 사용
        for label in {name, desc, file_name}:
            label = (label or "").strip()
            if not label:
                continue
            index.setdefault(label, entry)

# -----------------------------
# 4) UI
# -----------------------------
st.title("📘 필요 기술 / 약어 설명")

st.markdown(
    """
도안 설명이나 필요 기술 목록을 아래에 **그대로 붙여 넣으면**  
문장 안에 있는 **약어(k2tog, SSK, YO …)** 와  
**차트 기호 이름(예: ‘오른코 겹쳐 3코 모아뜨기’, ‘중심 5코 모아뜨기’ 등)** 을 동시에 찾아서 정리해 줍니다.
"""
)

text = st.text_area(
    "도안에서 필요한 기술/약어를 복사해서 붙여 넣으세요.",
    height=200,
    placeholder="예) k2tog, ssk, YO, 중심 5코 모아뜨기, 오른코 겹쳐 3코 모아뜨기 …",
)

st.divider()

# -----------------------------
# 5) 텍스트에서 용어 추출
#    - abbr_extract로 약어 찾기
#    - index에 있는 모든 키를 문장에서 검색
# -----------------------------
found_keys = set()

if text.strip():
    # 5-1. 약어 추출 (영문 약어 위주)
    try:
        abbrs = abbr_extract.extract(text, symbols)
        for a in abbrs:
            found_keys.add(a)
    except Exception:
        # 혹시 extract가 실패해도 다른 방식으로 찾기
        pass

    # 5-2. 모든 인덱스 키에 대해 서브스트링/단어 검색
    lowered = text.lower()
    for label in index.keys():
        if not label:
            continue
        # 한글은 그냥 포함 여부로, 영문/숫자는 단어 경계 기준으로
        if re.search(r"[a-zA-Z0-9]", label):
            # \blabel\b 형태로 찾기
            pattern = r"\b" + re.escape(label) + r"\b"
            if re.search(pattern, text, flags=re.IGNORECASE):
                found_keys.add(label)
        else:
            if label in text:
                found_keys.add(label)

# found_keys 를 실제 entry 로 변환
results = []
seen_entries = set()
for label in sorted(found_keys):
    entry = index.get(label)
    if not entry:
        continue
    # 같은 entry를 여러 label이 가리킬 수 있으므로 중복 제거
    key_id = (entry["kind"], entry.get("sheet"), entry["key"])
    if key_id in seen_entries:
        continue
    seen_entries.add(key_id)
    results.append((label, entry))

st.subheader(f"🔍 인식된 기술/약어: {len(results)}개")

if not results:
    st.info("텍스트에서 인식된 약어/차트 기호가 아직 없습니다. 위에 도안 내용을 붙여 넣어 보세요.")
else:
    # 약어/차트 따로 보여주기
    abbr_results = [item for item in results if item[1]["kind"] == "abbr"]
    chart_results = [item for item in results if item[1]["kind"] == "chart"]

    if abbr_results:
        st.markdown("### ✏️ 텍스트 약어 / 용어")
        for label, entry in abbr_results:
            name_ko = entry.get("name_ko") or entry.get("name_en") or entry["key"]
            desc = entry.get("desc_ko", "")
            st.markdown(f"**{name_ko}**  (`{label}`)")
            if desc:
                st.write(desc)
            st.markdown("---")

    if chart_results:
        st.markdown("### 🧵 차트 기호")
        cols = st.columns(3)
        idx = 0
        for label, entry in chart_results:
            col = cols[idx % 3]
            with col:
                if entry.get("image"):
                    st.image(entry["image"], width=120)
                title = entry.get("name_ko") or entry["key"]
                desc = entry.get("desc_ko", "")

                badge = f"{entry.get('sheet','차트')}"
                st.markdown(f"**{title}**  \n<small>{badge}</small>", unsafe_allow_html=True)
                if desc:
                    st.write(desc)
            idx += 1
        st.markdown("---")

st.page_link("HOME.py", label="⬅ 홈으로")