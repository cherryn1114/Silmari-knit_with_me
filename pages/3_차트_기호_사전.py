# pages/3_차트_기호_사전.py
# ---------------------------------------------------------
# assets/chart_from_excel/ 아래 폴더들을
# "엑셀 EXPORT.xlsx 의 시트 순서"대로 정렬해서
# 소분류(카테고리)별로 차트 기호 이미지를 보여주는 페이지
# → Sheet1 은 제외
# ---------------------------------------------------------

import streamlit as st
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import re

BASE = Path(__file__).resolve().parent.parent
CHART_ROOT = BASE / "assets" / "chart_from_excel"
XLSX_PATH = BASE / "data" / "EXPORT.xlsx"

# 화면에서 숨길 시트 이름들
EXCLUDED_SHEETS = {"Sheet1"}  # 필요하면 여기 추가(ex. {"Sheet1","테스트"})


def slugify_sheet_name(name: str) -> str:
    """시트 이름을 폴더 이름으로 안전하게 바꾸기 (엑셀 추출 스크립트와 동일 규칙)"""
    name = name.strip()
    name = re.sub(r"\s+", "_", name)  # 공백 → _
    name = re.sub(r'[\\/:*?"<>|]', "", name)  # 위험 문자 제거
    return name or "Sheet"


def get_sheet_names_in_order(xlsx_path: Path):
    """
    xl/workbook.xml 을 읽어서 시트 이름을 '엑셀에서 보이는 순서대로' 반환
    """
    if not xlsx_path.exists():
        return []

    with zipfile.ZipFile(xlsx_path, "r") as zf:
        wb_name = "xl/workbook.xml"
        if wb_name not in zf.namelist():
            return []

        ns = {"wb": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        root = ET.fromstring(zf.read(wb_name))
        names = []
        for sheet in root.findall("wb:sheets/wb:sheet", ns):
            nm = sheet.attrib.get("name", "Sheet")
            # 숨기기로 한 시트는 여기서부터 제외
            if nm in EXCLUDED_SHEETS:
                continue
            names.append(nm)
        return names


st.title("📈 차트 기호 사전 (엑셀 페이지 순서대로)")

# 0) 기본 폴더 체크
if not CHART_ROOT.exists():
    st.error(
        f"`{CHART_ROOT}` 폴더를 찾을 수 없습니다.\n\n"
        "먼저 터미널에서 `python lib/extract_excel_images.py` 를 실행해 "
        "엑셀에서 차트 기호 이미지를 추출해 주세요."
    )
    st.stop()

# 1) 엑셀 시트 순서 얻기 (Sheet1 제외)
sheet_names = get_sheet_names_in_order(XLSX_PATH)

# 2) 시트 순서대로, 해당 이름을 slugify 해서 폴더 매핑
categories = []  # [(folder_name, folder_path, [img_paths...]), ...]
excluded_slugs = {slugify_sheet_name(s) for s in EXCLUDED_SHEETS}

for sname in sheet_names:
    folder_name = slugify_sheet_name(sname)  # 예: "1코_기호"
    folder_path = CHART_ROOT / folder_name
    if not folder_path.exists() or not folder_path.is_dir():
        continue
    imgs = sorted(
        [p for p in folder_path.iterdir() if p.suffix.lower() in [".png", ".jpg", ".jpeg"]],
        key=lambda x: x.name,
    )
    if not imgs:
        continue
    categories.append((folder_name, folder_path, imgs))

# 엑셀에 없지만 폴더만 있는 경우도 뒤에 붙이기
existing_folder_names = {c[0] for c in categories}
for p in sorted(CHART_ROOT.iterdir()):
    if not p.is_dir():
        continue
    if p.name in existing_folder_names:
        continue
    if p.name in excluded_slugs:   # Sheet1 에 해당하는 폴더도 숨기기
        continue
    imgs = sorted(
        [x for x in p.iterdir() if x.suffix.lower() in [".png", ".jpg", ".jpeg"]],
        key=lambda x: x.name,
    )
    if not imgs:
        continue
    categories.append((p.name, p, imgs))

if not categories:
    st.error(
        f"`{CHART_ROOT}` 아래에서 이미지 파일을 찾지 못했습니다.\n\n"
        "엑셀에서 차트 기호를 그림으로 넣은 뒤, "
        "`python lib/extract_excel_images.py` 를 다시 실행해 주세요."
    )
    st.stop()

# 3) 소분류 선택 UI (시트 순서대로)
pretty_names = []
for folder_name, _, imgs in categories:
    label = folder_name.replace("_", " ")
    pretty_names.append(f"{label} ({len(imgs)}개)")

cat_options = ["전체 보기"] + pretty_names
choice = st.selectbox("소분류(엑셀 시트) 선택", cat_options)


def build_show_list():
    if choice == "전체 보기":
        return [(name, imgs) for (name, _, imgs) in categories]
    else:
        pure_label = choice.rsplit("(", 1)[0].strip()  # "1코 기호"
        fname = pure_label.replace(" ", "_")           # "1코_기호"
        for name, _, imgs in categories:
            if name == fname:
                return [(name, imgs)]
        return []


show_groups = build_show_list()
total_imgs = sum(len(imgs) for _, imgs in show_groups)
st.caption(f"현재 표시되는 기호 수: **{total_imgs}개**")

# 4) 렌더링: 시트 순서대로 섹션 + 이미지 그리드
for folder_name, imgs in show_groups:
    label = folder_name.replace("_", " ")
    st.subheader(f"🧵 {label} · {len(imgs)}개")

    cols = st.columns(5)
    for idx, img_path in enumerate(imgs):
        col = cols[idx % len(cols)]
        with col:
            st.image(str(img_path), use_container_width=True)
            st.caption(img_path.name)

    st.markdown("---")

# 5) 홈으로 돌아가기 링크 (없으면 무시)
try:
    st.page_link("HOME.py", label="🏠 홈으로 돌아가기", icon="🏠")
except Exception:
    pass