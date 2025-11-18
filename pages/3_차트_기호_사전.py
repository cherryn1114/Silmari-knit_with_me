# pages/3_차트_기호_사전.py
# 엑셀에서 읽은 "차트 기호 이름/설명" + 추출된 이미지(chart_from_excel)를
# 순서대로 매칭해서 보여주는 차트 기호 사전 페이지

import streamlit as st
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
XLSX_PATH = BASE / "data" / "moony_chart.xlsx"
IMG_DIR   = BASE / "assets" / "chart_from_excel"

st.set_page_config(
    page_title="차트 기호 사전",
    page_icon="📈",
    layout="wide",
)

st.title("📈 차트 도안 기호 사전")


# -----------------------------
# 1. 엑셀에서 이름/설명 읽기
# -----------------------------
@st.cache_data
def load_terms_from_excel(xlsx_path: Path):
    if not xlsx_path.exists():
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {xlsx_path}")

    # 첫 번째 시트 읽기
    df = pd.read_excel(xlsx_path)
    df = df.dropna(how="all")  # 완전 빈 행 제거
    df.columns = [str(c).strip() for c in df.columns]

    # 이름/설명 컬럼 추론
    cols = list(df.columns)

    def pick_col(candidates_ko_en):
        for c in cols:
            lower = c.lower()
            for key in candidates_ko_en:
                if key in lower:
                    return c
        return None

    # "기호 이름" / "기호명" / "이름" / "symbol" / "name" 등 찾기
    name_col = pick_col(["기호", "이름", "용어", "symbol", "name", "abbr"])
    # "설명" / "뜻" / "의미" / "description" 등 찾기
    desc_col = pick_col(["설명", "뜻", "의미", "description", "비고"])

    # 둘 다 못 찾으면 그냥 첫/두 번째 컬럼 사용
    if name_col is None:
        name_col = cols[0]
    if desc_col is None:
        desc_col = cols[1] if len(cols) > 1 else cols[0]

    records = []
    for _, row in df.iterrows():
        name = str(row.get(name_col, "")).strip()
        desc = str(row.get(desc_col, "")).strip()
        if not name:   # 이름이 비어 있으면 스킵
            continue
        records.append(
            {
                "name": name,
                "desc": desc,
            }
        )

    return records, name_col, desc_col


# -----------------------------
# 2. 이미지 목록 읽기
# -----------------------------
@st.cache_data
def load_images(img_dir: Path):
    if not img_dir.exists():
        return []
    imgs = [
        p for p in img_dir.iterdir()
        if p.suffix.lower() in [".png", ".jpg", ".jpeg"]
    ]
    # 파일명 순 정렬 (chart_001.png, chart_002.png, ...)
    imgs = sorted(imgs, key=lambda p: p.name)
    return imgs


# 데이터 로드
try:
    records, name_col_used, desc_col_used = load_terms_from_excel(XLSX_PATH)
except Exception as e:
    st.error(f"엑셀을 읽는 중 오류가 발생했어요:\n\n{e}")
    st.stop()

images = load_images(IMG_DIR)

if not images:
    st.error(
        f"`{IMG_DIR}` 폴더에 이미지가 없습니다.\n\n"
        "먼저 터미널에서 `python lib/extract_excel_images.py` 를 실행해 주세요."
    )
    st.stop()

st.caption(
    f"엑셀에서 읽은 용어 수: **{len(records)}개** "
    f"(이름 컬럼: `{name_col_used}`, 설명 컬럼: `{desc_col_used}`) · "
    f"추출된 이미지 수: **{len(images)}개**"
)

# -----------------------------
# 3. 순서대로 매칭하기
#    - 1행 → chart_001.png
#    - 2행 → chart_002.png
#    이런 식으로 인덱스 기반 매칭
# -----------------------------
n = min(len(records), len(images))
paired = []
for i in range(n):
    rec = records[i]
    img = images[i]
    paired.append(
        {
            "idx": i + 1,
            "name": rec["name"],
            "desc": rec["desc"],
            "img": img,
        }
    )

# 검색 UI
col_search, col_opt = st.columns([3, 1])
with col_search:
    q = st.text_input("검색 (이름/설명 일부를 입력하세요)", "")
with col_opt:
    show_index = st.checkbox("번호 표시", value=True)

def matches(rec, q):
    if not q:
        return True
    q = q.lower()
    return (q in rec["name"].lower()) or (q in rec["desc"].lower())

filtered = [r for r in paired if matches(r, q)]

st.caption(f"현재 표시: **{len(filtered)}개**")

# -----------------------------
# 4. 카드 형태로 렌더링 (이미지 + 이름 + 설명)
# -----------------------------
cols = st.columns(3)
for i, item in enumerate(filtered):
    col = cols[i % 3]
    with col:
        # 제목 줄
        if show_index:
            title = f"{item['idx']:03d}. {item['name']}"
        else:
            title = item["name"]

        st.markdown(f"### {title}")
        st.image(str(item["img"]), use_column_width=True)

        if item["desc"]:
            st.write(item["desc"])
        else:
            st.write("_설명 없음_")

st.markdown("---")
st.page_link("HOME.py", label="🏠 홈으로 돌아가기")