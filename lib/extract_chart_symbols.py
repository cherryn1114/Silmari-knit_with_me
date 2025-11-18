# lib/extract_chart_symbols.py
# ─────────────────────────────────────────
# 1) data/moony_chart.xlsx 에서
#    - 각 행의 텍스트(기호 이름/설명 등)
#    - 그 행에 붙어 있는 차트 그림
#    을 읽어와서
# 2) assets/chart_symbols/ 에 PNG로 저장
# 3) lib/chart_symbols.json 으로 메타데이터 저장
#
# ※ 엑셀 구조를 100% 알 수 없어서
#    - A열: "코드/약어" → key
#    - B열: "기호 이름"  → name
#    - C열: "설명"       → desc
#   이라고 가정해서 만들었어.
#   실제로 컬럼 구성이 다르면 A/B/C 열만 맞춰주면 돼.

from pathlib import Path
import io
import json

import pandas as pd
from openpyxl import load_workbook
from PIL import Image as PILImage

BASE = Path(__file__).resolve().parent

EXCEL_PATH = BASE.parent / "data" / "moony_chart.xlsx"
OUT_JSON   = BASE / "chart_symbols.json"
IMG_DIR    = BASE.parent / "assets" / "chart_symbols"

IMG_DIR.mkdir(parents=True, exist_ok=True)


def load_table_from_excel():
    """엑셀에서 텍스트 테이블 부분만 pandas DataFrame으로 읽기"""
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {EXCEL_PATH}")

    df = pd.read_excel(EXCEL_PATH)
    df = df.dropna(how="all")  # 완전 빈 행 제거

    # 컬럼명 공백 제거
    df.columns = [str(c).strip() for c in df.columns]

    # 아무 컬럼도 없으면 종료
    if df.shape[1] == 0:
        raise RuntimeError("엑셀에 유효한 컬럼이 없습니다.")

    return df


def extract_images_by_row():
    """
    openpyxl로 엑셀 안에 포함된 이미지들을 꺼내고,
    '위치한 행 번호(row)' 기준으로 매핑한다.

    반환:
        row → 이미지 파일명(str) 딕셔너리
    """
    wb = load_workbook(EXCEL_PATH, data_only=True)
    ws = wb.active  # 첫 번째 시트 사용 (다르면 여기만 바꾸면 됨)

    mapping = {}
    idx = 1

    # ws._images : openpyxl에서 워크시트에 붙은 그림 목록
    for img in getattr(ws, "_images", []):
        # 이미지가 붙어 있는 셀 위치 구하기
        anchor = getattr(img, "anchor", None)
        if anchor is None:
            continue

        # openpyxl 버전에 따라 anchor._from 에 있을 수 있음
        if hasattr(anchor, "_from"):
            cell_from = anchor._from
            row = cell_from.row + 1  # 0-based → 1-based
            col = cell_from.col + 1
        else:
            # 구버전 anchor: 직접 row/col 을 갖고 있을 수도 있음
            row = getattr(anchor, "row", None)
            col = getattr(anchor, "col", None)
            if row is None:
                continue

        # 이미지 바이너리 뽑아서 PNG로 저장
        try:
            # img._data() 가 바이너리를 돌려주는 경우가 많음
            bin_data = img._data()
            if callable(bin_data):
                bin_data = bin_data()
            pil = PILImage.open(io.BytesIO(bin_data))
        except Exception:
            # 혹시 실패하면 그냥 넘어감
            continue

        fname = f"row{row:03d}_{idx:02d}.png"
        out_path = IMG_DIR / fname
        pil.save(out_path)
        mapping[row] = fname
        idx += 1

    return mapping


def main():
    print("📥 엑셀 텍스트 테이블 읽는 중...")
    df = load_table_from_excel()
    # 편의를 위해 인덱스를 reset
    df = df.reset_index(drop=True)

    # 열 이름 가정: A열=코드/약어, B열=이름, C열=설명
    cols = list(df.columns)
    code_col = cols[0]
    name_col = cols[1] if len(cols) > 1 else cols[0]
    desc_col = cols[2] if len(cols) > 2 else name_col

    # 이미지 추출
    print("🖼 엑셀 안의 차트 그림 추출 중…")
    row_to_img = extract_images_by_row()

    symbols = {}
    for idx, row in df.iterrows():
        # 엑셀 상에서의 실제 행 번호 (1행 = 헤더라고 가정 → 데이터는 2행부터)
        excel_row = idx + 2

        key = str(row.get(code_col, "")).strip()
        if not key:
            # 키가 없으면 'rowXX' 로라도 기록
            key = f"row{excel_row:03d}"

        name = str(row.get(name_col, "")).strip()
        desc = str(row.get(desc_col, "")).strip()

        img_file = row_to_img.get(excel_row, "")

        symbols[key] = {
            "name": name,
            "desc": desc,
            "row": int(excel_row),
            "image": img_file,  # assets/chart_symbols 안의 파일명
        }

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(symbols, f, ensure_ascii=False, indent=2)

    print(f"✅ 기호 개수: {len(symbols)}개")
    print(f"📄 메타데이터: {OUT_JSON}")
    print(f"🖼 이미지 폴더: {IMG_DIR}")


if __name__ == "__main__":
    main()