# pages/3_차트_기호_사전.py

import os
import json
from pathlib import Path

import streamlit as st

# ---------------- 기본 설정 ----------------
st.set_page_config(
    page_title="실마리 — 차트 기호 사전",
    page_icon="🧵",
    layout="wide",
)

st.title("🧵 차트 기호 사전")

MANIFEST_PATH = Path("assets/chart_from_excel/manifest.json")

if not MANIFEST_PATH.exists():
    st.error("`assets/chart_from_excel/manifest.json` 파일을 찾을 수 없어요. "
             "먼저 `python lib/build_chart_manifest.py` 를 실행해서 매니페스트를 만들어 주세요.")
    st.stop()

# ---------------- 매니페스트 로드 ----------------
with MANIFEST_PATH.open(encoding="utf-8") as f:
    manifest = json.load(f)

# manifest 구조 예시:
# {
#   "1코 기호": {
#       "sheet": "1코 기호",
#       "img_dir": "assets/chart_from_excel/1코_기호",
#       "count_images": 32,
#       "count_named": 32,
#       "count_matched": 32,
#       "items": [
#           {"file": "chart_001.png", "abbr": "겉뜨기", "desc": "기본 겉뜨기"},
#           ...
#       ]
#   },
#   ...
# }

records = []
for sheet_title, info in manifest.items():
    img_dir = info.get("img_dir", "")
    for it in info.get("items", []):
        file = it.get("file")
        if not file:
            continue
        abbr = (it.get("abbr") or "").strip()
        desc = (it.get("desc") or "").strip()

        # img_dir 이 절대경로가 아니라면 assets 기준 상대경로라고 가정
        img_path = Path(img_dir) / file

        records.append(
            {
                "sheet": sheet_title,
                "img_path": str(img_path),
                "file": file,
                "abbr": abbr,
                "desc": desc,
            }
        )

if not records:
    st.warning("매니페스트에는 있지만 이미지 항목이 비어 있습니다.")
    st.stop()

# ---------------- 필터 UI ----------------
sheet_names = sorted({r["sheet"] for r in records})
sheet_option = st.selectbox(
    "소분류(엑셀 시트) 선택",
    options=["전체 보기"] + sheet_names,
    index=0,
)

if sheet_option == "전체 보기":
    shown = records
else:
    shown = [r for r in records if r["sheet"] == sheet_option]

st.caption(f"현재 표시되는 기호 수: **{len(shown)}개**")

# 시트별로 묶어서 보여주기
grouped = {}
for r in shown:
    grouped.setdefault(r["sheet"], []).append(r)

# ---------------- 렌더링 ----------------
N_COLS = 5

for sheet_title in sheet_names:
    if sheet_title not in grouped:
        continue

    items = grouped[sheet_title]
    st.markdown(f"### 🧵 {sheet_title} · {len(items)}개")

    cols = st.columns(N_COLS)
    idx = 0
    for r in items:
        col = cols[idx % N_COLS]
        idx += 1

        img_path = r["img_path"]
        file_name = r["file"]
        name = r["abbr"] or "(이름 없음)"
        desc = r["desc"]

        with col:
            # 이미지
            if Path(img_path).exists():
                st.image(img_path, use_column_width=True)
            else:
                st.error(f"이미지 없음\n`{img_path}`")

            # 이름 + 파일명
            st.markdown(f"**{name}**")
            st.caption(file_name)
            if desc:
                st.write(desc)

    st.divider()

# 맨 아래 홈으로 돌아가기 링크 (원하면 삭제 가능)
st.page_link("HOME.py", label="⬅️ 홈으로")