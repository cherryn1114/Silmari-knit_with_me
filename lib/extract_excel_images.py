# lib/extract_excel_images.py
# 엑셀(xlsx)을 ZIP처럼 열어서 xl/media 안에 들어있는
# 모든 이미지 파일을 assets/chart_from_excel 폴더에 복사한다.

from pathlib import Path
import zipfile
import shutil

# 프로젝트 루트 기준 경로
BASE = Path(__file__).resolve().parent.parent

# ❗엑셀 파일 이름이 정확히 맞는지 확인해서 필요하면 수정하세요
XLSX_PATH = BASE / "data" / "moony_chart.xlsx"

OUT_DIR = BASE / "assets" / "chart_from_excel"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_from_zip():
    if not XLSX_PATH.exists():
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {XLSX_PATH}")

    print(f"📘 엑셀 파일: {XLSX_PATH}")

    count = 0
    with zipfile.ZipFile(XLSX_PATH, "r") as zf:
        # xl/media/ 안에 들어있는 모든 파일(이미지들)을 찾는다.
        media_files = [name for name in zf.namelist() if name.startswith("xl/media/")]

        if not media_files:
            print("⚠️ xl/media/ 안에서 이미지를 찾지 못했습니다.")
            return

        # 정렬해서 순서대로 저장
        media_files.sort()

        for idx, inner_name in enumerate(media_files, start=1):
            ext = Path(inner_name).suffix.lower()  # .png, .jpg 등
            out_name = f"chart_{idx:03d}{ext}"
            out_path = OUT_DIR / out_name

            with zf.open(inner_name) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

            print(f"  ✅ {inner_name} → {out_name}")
            count += 1

    print(f"\n🎉 총 추출된 이미지 수: {count}개")
    print(f"📂 저장 폴더: {OUT_DIR}")


if __name__ == "__main__":
    extract_from_zip()
