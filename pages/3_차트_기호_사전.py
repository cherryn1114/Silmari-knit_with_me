# pages/3_차트_기호_사전.py

import streamlit as st
from pathlib import Path
from lib import parser

# -----------------------------
# 기본 설정 & 경로
# -----------------------------
st.title("🧵 차트 도안 기호 사전")

# 이미지가 들어 있는 폴더 (assets/chart)
ASSET_DIR = Path("assets") / "chart"

# -----------------------------
# 1) 차트용 사전 로드 (chart_symbols.json 우선)
# -----------------------------
lib = {}
source_label = ""

try:
    # extract_chart_symbols.py를 돌려서 만든 결과가 있으면 이걸 우선 사용
    lib = parser.load_lib("chart_symbols.json")
    source_label = "chart_symbols.json (차트 기호만)"
except FileNotFoundError:
    # 없으면 기본 symbols.json 전체 사용
    lib = parser.load_lib("symbols.json")
    source_label = "symbols.json (전체 약어 사전)"

if not lib:
    st.error("차트 기호 사전을 불러오지 못했습니다. lib/symbols.json 또는 lib/chart_symbols.json을 확인하세요.")
    st.stop()

# dict를 key 기준으로 정렬
items = sorted(lib.items(), key=lambda kv: kv[0].lower())

# -----------------------------
# 2) 검색 / 필터 UI
# -----------------------------
col1, col2 = st.columns([2, 1])
with col1:
    q = st.text_input("검색 (약어 / 한글 / 영어 / 설명)", "")
with col2:
    only_chart_image = st.checkbox("이미지 있는 항목만 보기", value=False)

st.caption(f"불러온 사전: **{source_label}** · 총 항목 수: **{len(items)}**")

# 간단 매칭 함수
def matches(item_key: str, item_val: dict, query: str) -> bool:
    if not query:
        return True
    q_low = query.lower()
    name_en = (item_val.get("name_en") or "").lower()
    name_ko = (item_val.get("name_ko") or "").lower()
    desc    = (item_val.get("desc_ko") or "").lower()
    aliases = " ".join(item_val.get("aliases", []))

    if q_low in item_key.lower():
        return True
    if q_low in name_en or q_low in name_ko or q_low in desc:
        return True
    if q_low in aliases.lower():
        return True
    return False

# slugify: key를 이미지 파일명으로 추정할 때 사용 (chart_image가 없을 경우 대비)
def slugify(s: str) -> str:
    s = s.strip()
    s = s.replace(" ", "_")
    s = s.replace("/", "_")
    s = "".join(ch for ch in s if ch.isalnum() or ch in ["_", "-"])
    return s or "symbol"

# -----------------------------
# 3) 항목 렌더링
# -----------------------------
shown = 0

for key, val in items:
    if not matches(key, val, q):
        continue

    # chart_image 필드가 있으면 우선 사용, 없으면 key 기반으로 추정
    img_name = val.get("chart_image") or (slugify(key) + ".png")
    img_path = ASSET_DIR / img_name

    has_image = img_path.exists()

    if only_chart_image and not has_image:
        continue

    name_ko = val.get("name_ko", "")
    name_en = val.get("name_en", "")

    # 각 기호를 접이식(expander) 카드로 표시
    with st.expander(f"{key} — {name_ko or name_en}"):
        cols = st.columns([1, 2])

        # ▸ 왼쪽: 차트 이미지 (또는 대체 텍스트)
        with cols[0]:
            if has_image:
                st.image(str(img_path), use_column_width=True, caption=img_name)
            else:
                chart_sym = val.get("chart_symbol", "")
                if chart_sym:
                    st.markdown(f"### `{chart_sym}`")
                    st.caption("등록된 이미지가 없어서 심볼 텍스트만 표시합니다.")
                else:
                    st.warning("🖼 등록된 차트 이미지가 없습니다.\nassets/chart/ 폴더와 chart_image 필드를 확인하세요.")

        # ▸ 오른쪽: 이름 / 설명 / 기타 정보
        with cols[1]:
            st.markdown(f"**영문 이름**: {name_en or '-'}")
            st.markdown(f"**한국어 이름**: {name_ko or '-'}")

            desc = val.get("desc_ko") or "(설명 없음)"
            st.write(desc)

            # delta(코수 증감) 정보가 있으면 함께 표시
            delta = val.get("delta", None)
            try:
                d_int = int(delta)
                if d_int > 0:
                    st.info(f"🔺 이 기법을 한 번 사용하면 **코 수가 +{d_int}코** 늘어납니다.")
                elif d_int < 0:
                    st.info(f"🔻 이 기법을 한 번 사용하면 **코 수가 {d_int}코** 줄어듭니다.")
            except Exception:
                pass

            # 비교(compare) 필드가 있으면 함께 보여주기 (예: m1L vs m1R)
            if val.get("compare"):
                st.markdown("**비교 기법:** " + ", ".join(val["compare"]))

    shown += 1

if shown == 0:
    st.info("조건에 맞는 차트 기호가 없습니다. 검색어/필터를 확인해 보세요.")

st.divider()
st.caption("※ chart_symbols.json이 있으면 그것을 사용하고, 없으면 symbols.json 전체를 기반으로 차트 기호를 보여줍니다. 이미지 파일은 assets/chart/ 폴더에 두면 자동으로 연결됩니다.")