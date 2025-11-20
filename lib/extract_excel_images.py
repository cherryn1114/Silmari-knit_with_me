# lib/extract_excel_images.py
# ---------------------------------------------------------
# data/EXPORT.xlsx 안의 시트(페이지)별 차트 기호 이미지를
# 시트 이름 기준으로 폴더를 나누어 추출한다.
#
# 예시:
#   시트 "1코 기호 분류" → assets/chart_from_excel/1코_기호_분류/chart_001.png ...
#   시트 "1코 2단 기호" → assets/chart_from_excel/1코_2단_기호/chart_001.png ...
#
# 정렬 규칙(각 시트 내):
#   1) 왼쪽 열(col 값이 작은 것)부터
#   2) 같은 열 안에서는 위에서 아래(row 값이 작은 것부터)
# ---------------------------------------------------------

from pathlib import Path
import zipfile
import shutil
import xml.etree.ElementTree as ET
import re

BASE = Path(__file__).resolve().parent.parent

# ✅ 여기서 사용할 엑셀 파일 이름
XLSX_PATH = BASE / "data" / "EXPORT.xlsx"

OUT_ROOT = BASE / "assets" / "chart_from_excel"
OUT_ROOT.mkdir(parents=True, exist_ok=True)


def slugify_sheet_name(name: str) -> str:
    """시트 이름을 폴더 이름으로 안전하게 바꾸기 (공백→_, 특수문자 제거)"""
    name = name.strip()
    name = re.sub(r"\s+", "_", name)  # 공백 → _
    name = re.sub(r'[\\/:*?"<>|]', "", name)  # 위험 문자 제거
    return name or "Sheet"


def load_sheet_name_map(zf: zipfile.ZipFile):
    """
    workbook.xml / workbook.xml.rels 를 읽어서
    sheet XML 경로 → 시트 이름 매핑을 만든다.

    반환: dict[str, str]  예) {"xl/worksheets/sheet1.xml": "1코 기호 분류", ...}
    """
    ns = {
        "wb": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }

    wb_xml_name = "xl/workbook.xml"
    rels_xml_name = "xl/_rels/workbook.xml.rels"

    if wb_xml_name not in zf.namelist():
        raise FileNotFoundError("xl/workbook.xml 이 엑셀 파일 안에 없습니다.")

    wb_root = ET.fromstring(zf.read(wb_xml_name))

    # r:id → 시트 이름
    rId_to_name = {}
    for sheet in wb_root.findall("wb:sheets/wb:sheet", ns):
        name = sheet.attrib.get("name", "Sheet")
        r_id = sheet.attrib.get("{%s}id" % ns["r"])
        if r_id:
            rId_to_name[r_id] = name

    if rels_xml_name not in zf.namelist():
        raise FileNotFoundError("xl/_rels/workbook.xml.rels 이 엑셀 파일 안에 없습니다.")

    rels_root = ET.fromstring(zf.read(rels_xml_name))

    sheet_path_to_name = {}
    for rel in rels_root:
        if not rel.tag.endswith("Relationship"):
            continue
        r_id = rel.attrib.get("Id")
        target = (rel.attrib.get("Target") or "").replace("\\", "/")
        if not (r_id and target):
            continue

        if r_id not in rId_to_name:
            continue

        # 보통 "worksheets/sheet1.xml" 형태 → "xl/worksheets/sheet1.xml" 로 보정
        if not target.startswith("xl/"):
            target = f"xl/{target.lstrip('/')}"
        sheet_xml_path = target
        sheet_name = rId_to_name[r_id]
        sheet_path_to_name[sheet_xml_path] = sheet_name

    return sheet_path_to_name


def sheet_to_drawing_map(zf: zipfile.ZipFile, sheet_path_to_name: dict):
    """
    각 worksheet XML에 연결된 drawing XML 목록을 찾는다.
    반환: dict[sheet_name] = [drawing_xml_path, ...]
    """
    ns = {
        "ws": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }

    result = {}

    for sheet_xml, sheet_name in sheet_path_to_name.items():
        if sheet_xml not in zf.namelist():
            continue

        sheet_xml_path = Path(sheet_xml)

        # ✅ 시트별 rels 파일 경로: xl/worksheets/_rels/sheet1.xml.rels
        sheet_rel_path = (
            sheet_xml_path.parent  # xl/worksheets
            / "_rels"
            / f"{sheet_xml_path.name}.rels"  # sheet1.xml.rels
        )
        sheet_rel = str(sheet_rel_path).replace("\\", "/")

        rId_to_drawing = {}
        if sheet_rel in zf.namelist():
            rels_root = ET.fromstring(zf.read(sheet_rel))
            for rel in rels_root:
                if not rel.tag.endswith("Relationship"):
                    continue
                r_id = rel.attrib.get("Id")
                target = (rel.attrib.get("Target") or "").replace("\\", "/")
                r_type = rel.attrib.get("Type", "")
                if "/drawing" not in r_type:
                    continue

                # "../drawings/drawing1.xml" → "xl/drawings/drawing1.xml"
                if target.startswith("../"):
                    target = "xl/" + target[3:]
                elif not target.startswith("xl/"):
                    target = "xl/" + target.lstrip("/")
                rId_to_drawing[r_id] = target

        # 시트 XML 안에서 drawing 요소의 r:id 찾기
        draw_paths = []
        root = ET.fromstring(zf.read(sheet_xml))
        for draw in root.findall("ws:drawing", ns):
            r_id = draw.attrib.get("{%s}id" % ns["r"])
            if r_id and r_id in rId_to_drawing:
                draw_paths.append(rId_to_drawing[r_id])

        if draw_paths:
            # 중복 제거
            result[sheet_name] = list(dict.fromkeys(draw_paths))

    return result


def parse_drawing(zf: zipfile.ZipFile, drawing_xml_name: str):
    """
    xl/drawings/drawingN.xml 하나를 읽어서
    (col, row, media_path) 리스트를 반환
    """
    ns = {
        "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }

    # drawing.xml 에 대응하는 relationships 파일: rId → media 경로
    rels_name = drawing_xml_name.replace("drawings/", "drawings/_rels/") + ".rels"
    rels_map = {}

    if rels_name in zf.namelist():
        rels_root = ET.fromstring(zf.read(rels_name))
        for rel in rels_root:
            if not rel.tag.endswith("Relationship"):
                continue
            r_id = rel.attrib.get("Id")
            target = (rel.attrib.get("Target") or "").replace("\\", "/")
            if not (r_id and target):
                continue
            # "../media/image1.png" → "xl/media/image1.png"
            if target.startswith("../"):
                target_norm = "xl/" + target[3:]
            elif not target.startswith("xl/"):
                target_norm = "xl/" + target.lstrip("/")
            else:
                target_norm = target
            rels_map[r_id] = target_norm

    root = ET.fromstring(zf.read(drawing_xml_name))

    entries = []

    # oneCellAnchor / twoCellAnchor
    anchors = []
    anchors += root.findall("xdr:oneCellAnchor", ns)
    anchors += root.findall("xdr:twoCellAnchor", ns)

    for anchor in anchors:
        from_node = anchor.find("xdr:from", ns)
        if from_node is None:
            continue

        col_el = from_node.find("xdr:col", ns)
        row_el = from_node.find("xdr:row", ns)
        if col_el is None or row_el is None:
            continue

        try:
            col = int(col_el.text or 0)
            row = int(row_el.text or 0)
        except ValueError:
            continue

        pic = anchor.find("xdr:pic", ns)
        if pic is None:
            continue

        blip = pic.find(".//a:blip", ns)
        if blip is None:
            continue

        r_embed = blip.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
        )
        if not r_embed:
            continue

        media_path = rels_map.get(r_embed)
        if not media_path:
            continue

        if "media/" not in media_path:
            continue

        entries.append({"col": col, "row": row, "media": media_path})

    return entries


def extract_grouped_by_sheet():
    if not XLSX_PATH.exists():
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {XLSX_PATH}")

    print(f"📘 엑셀 파일: {XLSX_PATH}")

    with zipfile.ZipFile(XLSX_PATH, "r") as zf:
        # 1) sheet XML → 시트 이름 매핑
        sheet_path_to_name = load_sheet_name_map(zf)

        # 2) 시트별 drawing XML 목록
        sheet_to_drawings = sheet_to_drawing_map(zf, sheet_path_to_name)

        if not sheet_to_drawings:
            print("⚠️ 시트에 연결된 drawing(그림서식)을 찾지 못했습니다.")
            return

        total_count = 0

        print("\n=== 시트별 차트 기호 추출 시작 ===")
        for sheet_name, drawing_list in sheet_to_drawings.items():
            safe = slugify_sheet_name(sheet_name)
            out_dir = OUT_ROOT / safe
            out_dir.mkdir(parents=True, exist_ok=True)

            sheet_entries = []

            for dxml in drawing_list:
                if dxml not in zf.namelist():
                    continue
                entries = parse_drawing(zf, dxml)
                sheet_entries.extend(entries)

            if not sheet_entries:
                print(f"▶ 시트 '{sheet_name}' 에서 추출된 기호가 없습니다.")
                continue

            # (col, row) 정렬 → 왼쪽 열부터, 위에서 아래로
            sheet_entries.sort(key=lambda e: (e["col"], e["row"]))

            # media 중복 제거 + 실제 파일 존재 여부 확인
            seen_media = set()
            ordered = []
            for e in sheet_entries:
                m = e["media"]
                if m in seen_media:
                    continue
                if m not in zf.namelist():
                    continue
                seen_media.add(m)
                ordered.append(e)

            # 실제 추출
            count_sheet = 0
            for idx, e in enumerate(ordered, start=1):
                inner = e["media"]
                ext = Path(inner).suffix or ".png"
                out_name = f"chart_{idx:03d}{ext}"
                out_path = out_dir / out_name

                with zf.open(inner) as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

                print(f"  🖼 [{sheet_name}] col={e['col']}, row={e['row']} → {safe}/{out_name}")
                count_sheet += 1
                total_count += 1

            print(f"▶ 시트 '{sheet_name}' 추출 완료: {count_sheet}개 (폴더: {out_dir})")

        print("\n=== 요약 ===")
        for sheet_name in sheet_to_drawings.keys():
            safe = slugify_sheet_name(sheet_name)
            folder = OUT_ROOT / safe
            if folder.exists():
                n_files = len([p for p in folder.iterdir() if p.is_file()])
            else:
                n_files = 0
            print(f" - {sheet_name} ({safe}): {n_files}개")

        print(f"\n🎉 전체 추출된 이미지 수(모든 시트 합계): {total_count}개")
        print(f"📂 루트 폴더: {OUT_ROOT}")


if __name__ == "__main__":
    extract_grouped_by_sheet()