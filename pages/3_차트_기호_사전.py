# pages/3_차트_기호_사전.py

import streamlit as st
from pathlib import Path
from lib import parser

st.title("🧵 차트 도안 기호 사전")

# gen_chart_images_v3.py 에서 사용한 키 목록과 동일하게 맞춰야 함
CHART_KEYS = [
    "k",
    "p",
    "yo",
    "sl",
    "ktbl",
    "ptbl",
    "kwise",
    "pwise",
    "M1",
    "M1L",
    "M1R",
    "Inc",
    "독일식 경사뜨기",
    "옛 노르웨이식 코잡기",
    "k2tog",
    "Knit 3 stitches together (k3tog)",
    "p2tog",
    "SSK",
    "SSP",
    "Tog",
    "1/1 LC",
    "1/1 RC",
    "2/2 LC",
    "2/2 RC",
    "오른코 위 2코와 1코 교차뜨기",
    "오른코 위 2코와 1코(안뜨기) 교차뜨기",
    "오른코 위 3코 교차뜨기",
    "오른코 위 3코와 1코(안뜨기) 교차뜨기",
    "오른코에 꿴 매듭뜨기 (3코)",
    "왼코 위 2코와 1코 교차뜨기",
    "왼코 위 2코와 1코(안뜨기) 교차뜨기",
    "왼코 위 3코 교차뜨기",
    "왼코 위 3코와 1코(안뜨기) 교차뜨기",
    "걸러뜨기",
]

ASSET_DIR = Path("assets") / "chart"


def slugify(s: str) -> str:
    s = s.strip()
    s = s.replace(" ", "_").replace("/", "_")
    s = "".join(ch for ch in s if ch.isalnum() or ch in "_-")
    return s or "symbol"


# 1) symbols.json + symbols_extra.json 병합
base = parser.load_lib("symbols.json")
try:
    extra = parser.load_lib("symbols_extra.json")
except FileNotFoundError:
    extra = {}

merged = {**base, **extra}

# 2) 차트 대상만 필터
chart_items = {
    k: v for k, v in merged.items()
    if k in CHART_KEYS
}

# 정렬
items = sorted(chart_items.items(), key=lambda kv: kv[0].lower())

st.caption(f"총 차트 기호 항목: **{len(items)}개**")

# 검색 UI
col1, col2 = st.columns([2, 1])
with col1:
    q = st.text_input("검색 (약어 / 한글 / 영어 / 설명)", "")
with col2:
    only_with_image = st.checkbox("이미지 있는 것만 보기", value=False)


def matches(key: str, val: dict, query: str) -> bool:
    if not query:
        return True
    ql = query.lower()
    name_en = (val.get("name_en") or "").lower()
    name_ko = (val.get("name_ko") or "").lower()
    desc = (val.get("desc_ko") or "").lower()
    aliases = " ".join(val.get("aliases", [])).lower()

    if ql in key.lower():
        return True
    if ql in name_en or ql in name_ko or ql in desc:
        return True
    if ql in aliases:
        return True
    return False


shown = 0

for key, val in items:
    if not matches(key, val, q):
        continue

    img_name = slugify(key) + ".png"
    img_path = ASSET_DIR / img_name
    has_image = img_path.exists()

    if only_with_image and not has_image:
        continue

    name_ko = val.get("name_ko", "")
    name_en = val.get("name_en", "")

    title = f"{key}"
    if name_ko or name_en:
        title += f" — {name_ko or name_en}"

    with st.expander(title):
        cols = st.columns([1, 2])

        # 왼쪽: 이미지
        with cols[0]:
            if has_image:
                st.image(str(img_path), use_column_width=True, caption=img_name)
            else:
                st.warning("🖼 등록된 차트 이미지가 없습니다.\nassets/chart/ 폴더를 확인하세요.")

        # 오른쪽: 설명
        with cols[1]:
            st.markdown(f"**영문 이름**: {name_en or '-'}")
            st.markdown(f"**한국어 이름**: {name_ko or '-'}")

            desc = val.get("desc_ko") or "(설명 없음)"
            st.write(desc)

            # delta(코 증감) 있으면 표시
            try:
                d = int(val.get("delta", 0))
                if d > 0:
                    st.info(f"🔺 이 기법을 한 번 사용하면 **코 수가 +{d}코** 늘어납니다.")
                elif d < 0:
                    st.info(f"🔻 이 기법을 한 번 사용하면 **코 수가 {d}코** 줄어듭니다.")
            except Exception:
                pass

    shown += 1

if shown == 0:
    st.info("조건에 맞는 차트 기호가 없습니다. 검색어/필터를 확인해보세요.")

st.divider()
st.caption(
    "※ 이 페이지는 symbols.json(+symbols_extra.json)에 정의된 용어 중 "
    "차트로 표현 가능한 용어들만 모아, assets/chart/ 폴더의 이미지를 연결해서 보여줍니다."
)