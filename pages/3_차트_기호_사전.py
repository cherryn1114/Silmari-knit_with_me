# pages/3_차트_기호_사전.py
# 엑셀에서 추출된 차트 기호 이미지들(assets/chart_from_excel)을
# 그대로 갤러리 형태로 보여주는 페이지

import streamlit as st
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
IMG_DIR = BASE / "assets" / "chart_from_excel"

st.set_page_config(
    page_title="차트 기호 사전",
    page_icon="📈",
    layout="wide",
)

st.title("📈 차트 도안 기호 사전 (엑셀 이미지 갤러리)")

if not IMG_DIR.exists():
    st.error(f"`{IMG_DIR}` 폴더를 찾을 수 없습니다.\n\n먼저 `python lib/extract_excel_images.py` 를 실행해 주세요.")
    st.stop()

# 폴더 안의 이미지 파일들 찾기
image_files = sorted(
    [p for p in IMG_DIR.iterdir() if p.suffix.lower() in [".png", ".jpg", ".jpeg"]],
    key=lambda p: p.name,
)

if not image_files:
    st.warning("📂 `assets/chart_from_excel` 안에 표시할 이미지가 없습니다.")
    st.stop()

st.caption(f"추출된 차트 기호 이미지 수: **{len(image_files)}개**")

# 검색(파일명 기준, 간단 필터)
q = st.text_input("파일명으로 필터링 (예: 001, knit, purl 등 포함되는 문자열)", "")

filtered = []
for img in image_files:
    name = img.name.lower()
    if q.strip():
        if q.strip().lower() not in name:
            continue
    filtered.append(img)

st.caption(f"현재 표시: **{len(filtered)}개**")

# 3열 갤러리 레이아웃
cols = st.columns(3)

for idx, img_path in enumerate(filtered):
    col = cols[idx % 3]
    with col:
        st.image(str(img_path), use_column_width=True)
        st.markdown(f"<sub>{img_path.name}</sub>", unsafe_allow_html=True)

st.markdown("---")
st.page_link("HOME.py", label="⬅️ 홈으로 돌아가기", icon="🏠")
