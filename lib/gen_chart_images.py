# lib/gen_chart_images.py
"""
symbols.json + symbols_extra.json에 들어 있는 용어 중
'차트로 표현할 수 있는 것들'만 골라서

- assets/chart/ 폴더에
  흰 배경 + 약어 + 영문이름이 들어간 PNG 아이콘을 생성해 줍니다.

터미널에서:
    cd /workspaces/Silmari-knit_with_me
    python lib/gen_chart_images.py
"""

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent

SYMBOLS_PATH = BASE / "symbols.json"
EXTRA_PATH   = BASE / "symbols_extra.json"
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
# 차트로 표현 가능한지 대략 판단
# (네 사전에 있는 "2/2 LC, 2/1 RPC, k2tog, ssk" 등 자동 포착)
# -----------------------------
CABLE_PATTERNS = [
    r"\d+/\d+",       # 2/2, 1/2, 3/1, ...
    r"\bRC\b", r"\bLC\b",
    r"RPC", r"LPC", r"Cable", r"cable", r"cross",
]

DECREASE_KEYS = [
    "tog", "k2tog", "p2tog", "k3tog", "p3tog",
    "ssk", "ssp", "skp", "cdd", "cddp",
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

    # delta 값이 +/- 이면 보통 증감 기법
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

    # 이름 안에 cable / cross / 꽈배기 / 교차 가 들어가는 경우
    name_en = (item.get("name_en") or "").lower()
    name_ko = (item.get("name_ko") or "").lower()
    if "cable" in name_en or "cross" in name_en or "꽈배기" in name_ko or "교차" in name_ko:
        return True

    return False


def slugify(s: str) -> str:
    s = s.strip()
    s = s.replace(" ", "_")
    s = s.replace("/", "_")
    s = "".join(ch for ch in s if (ch.isalnum() or ch in ["_", "-"]))
    return s or "symbol"


def create_icon_png(key: str, name_en: str) -> str:
    """
    흰 배경 + 테두리 + 가운데 약어 + 아래 영문 이름
    형태의 심플한 PNG 아이콘 생성
    """
    size = 600  # 해상도
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)

    # 바깥 사각형
    margin = 40
    draw.rectangle(
        (margin, margin, size - margin, size - margin),
        outline="black",
        width=6,
    )

    # 폰트 준비
    try:
        font_big = ImageFont.truetype("arial.ttf", 80)
        font_small = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 가운데 약어 텍스트
    text = key
    w, h = draw.textsize(text, font=font_big)
    draw.text(
        ((size - w) / 2, (size - h) / 2 - 40),
        text,
        fill="black",
        font=font_big,
    )

    # 아래 영어 이름 (있으면)
    if name_en:
        w2, h2 = draw.textsize(name_en, font=font_small)
        draw.text(
            ((size - w2) / 2, size - h2 - 40),
            name_en,
            fill="black",
            font=font_small,
        )

    filename = slugify(key) + ".png"
    out_path = IMG_DIR / filename
    img.save(out_path)
    return filename


# -----------------------------
# 메인 로직
# -----------------------------
def main():
    count = 0
    for key, item in merged.items():
        if not is_chartable(key, item):
            continue

        name_en = item.get("name_en", "")
        fname = create_icon_png(key, name_en)
        count += 1
        print(f"  - {key} → assets/chart/{fname}")

    print("===================================")
    print(f"✅ 생성된 차트 이미지 개수: {count}개")
    print("→ assets/chart/ 폴더를 확인하세요.")


if __name__ == "__main__":
    main()