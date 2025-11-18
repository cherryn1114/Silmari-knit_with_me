# lib/extract_chart_symbols.py
"""
symbols.json + symbols_extra.json 에서
'차트 기호로 표현 가능한 용어'만 골라서
lib/chart_symbols.json 으로 저장하고,
assets/chart/ 아래에 기호 이미지를 생성하는 스크립트.

터미널에서:
    cd /workspaces/Silmari-knit_with_me
    python lib/extract_chart_symbols.py
"""

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent

SYMBOLS_PATH = BASE / "symbols.json"
EXTRA_PATH   = BASE / "symbols_extra.json"
OUT_JSON     = BASE / "chart_symbols.json"
IMG_DIR      = ROOT / "assets" / "chart"
IMG_DIR.mkdir(parents=True, exist_ok=True)


def load_json(p: Path) -> dict:
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as f:
        return json.load(f)


base = load_json(SYMBOLS_PATH)
extra = load_json(EXTRA_PATH)
merged = {**base, **extra}


# -----------------------------
# 차트 기호로 쓸 수 있는지 판단
# -----------------------------
CABLE_PATTERNS = [
    r"\d+/\d+",       # 2/2, 2/1, 3/1 등
    r"\bRC\b", r"\bLC\b",
    r"RPC", r"LPC", r"Cable", r"cable", r"twist", r"cross",
]

DECREASE_KEYS = [
    "tog", "k2tog", "p2tog", "k3tog", "p3tog",
    "ssk", "ssp", "skp", "cdd", "cddp", "k2tog tbl",
]

INCREASE_KEYS = [
    "yo", "m1", "m1l", "m1r", "kfb", "pfb", "inc",
]

BASIC_KEYS = [
    "k", "p", "tbl", "ktbl", "ptbl", "k1-b", "sl", "slip",
]

def is_chartable(key: str, item: dict) -> bool:
    k_lower = key.lower()

    # 기본 스티치
    if k_lower in [b.lower() for b in BASIC_KEYS]:
        return True

    # 증가
    if any(w in k_lower for w in [x.lower() for x in INCREASE_KEYS]):
        return True

    # 감소
    if any(w in k_lower for w in [x.lower() for x in DECREASE_KEYS]):
        return True

    # delta 값이 +/- 인 것도 차트 가능성 ↑
    try:
        d = int(item.get("delta", 0))
        if d != 0:
            return True
    except Exception:
        pass

    # 케이블 / 교차
    for pat in CABLE_PATTERNS:
        if re.search(pat, key, flags=re.IGNORECASE):
            return True

    # name_en / name_ko 에 cable, cross 가 들어간 경우
    name_en = (item.get("name_en") or "").lower()
    name_ko = (item.get("name_ko") or "").lower()
    if "cable" in name_en or "cross" in name_en or "꽈배기" in name_ko or "교차" in name_ko:
        return True

    return False


def slugify(s: str) -> str:
    # 파일 이름에 쓰기 안전한 형태로 변환
    s = s.strip()
    s = s.replace(" ", "_")
    s = s.replace("/", "_")
    s = re.sub(r"[^A-Za-z0-9_\-]", "", s)
    if not s:
        s = "symbol"
    return s


# -----------------------------
# 1) 차트 가능 항목만 모아서 JSON 생성
# -----------------------------
chart_symbols = {}

for key, item in merged.items():
    if not is_chartable(key, item):
        continue

    base_entry = dict(item)  # 복사
    # chart_image 파일명 제안
    filename = slugify(key) + ".png"

    base_entry.setdefault("chart_symbol", "")   # 나중에 수동 추가해도 됨
    base_entry["chart_image"] = filename

    chart_symbols[key] = base_entry

# 저장
OUT_JSON.write_text(json.dumps(chart_symbols, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"✅ 차트 기호로 판단된 항목 수: {len(chart_symbols)}개")
print(f"→ lib/chart_symbols.json 으로 저장 완료")


# -----------------------------
# 2) 각 항목에 대해 단순 차트 이미지 생성
#    (흰 배경 + 기호 텍스트)
# -----------------------------
def create_icon_png(key: str, filename: str):
    size = 600  # 해상도 (원하면 1200으로 키워도 됨)
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)

    # 바깥 사각형
    margin = 40
    draw.rectangle(
        (margin, margin, size - margin, size - margin),
        outline="black",
        width=6,
    )

    # 텍스트: 가운데에는 약어, 아래에는 영문 이름 일부
    text = key
    # 기본 폰트 (환경 의존적이라 family는 지정X)
    try:
        font = ImageFont.truetype("arial.ttf", 80)
        small = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        font = ImageFont.load_default()
        small = ImageFont.load_default()

    # 가운데 큰 텍스트
    w, h = draw.textsize(text, font=font)
    draw.text(
        ((size - w) / 2, (size - h) / 2 - 40),
        text,
        fill="black",
        font=font,
    )

    # 아래 작은 설명(있으면)
    desc = chart_symbols[key].get("name_en") or ""
    if desc:
        w2, h2 = draw.textsize(desc, font=small)
        draw.text(
            ((size - w2) / 2, size - h2 - 40),
            desc,
            fill="black",
            font=small,
        )

    out_path = IMG_DIR / filename
    img.save(out_path)
    return out_path


print("🖼 차트 기호 PNG 생성 중…")
for k, v in chart_symbols.items():
    fname = v["chart_image"]
    path = create_icon_png(k, fname)
    print(f"  - {k} → {path.relative_to(ROOT)}")

print("✅ 이미지 생성 완료!")
print("   assets/chart/ 폴더를 확인하세요.")