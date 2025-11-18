"""
lib/gen_chart_images_v2.py
모든 차트 가능한 용어를 국제표준 차트 기호 PNG로 자동 생성하는 스크립트
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "charts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 캔버스 사이즈
W, H = 300, 300
LINE = 8  # 선 굵기
COLOR = "black"
BG = "white"

# 기본 폰트
try:
    FONT = ImageFont.truetype("Arial.ttf", 40)
except:
    FONT = ImageFont.load_default()


def save_icon(name, drawer):
    """이름(name)과 drawer(draw function)를 받아 이미지 파일 생성"""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    drawer(draw)
    img.save(OUT_DIR / f"{name}.png")


# ----------- 기본 스티치 ----------------

def draw_knit(draw):
    # knit symbol: 빈 칸 또는 작은 V
    draw.line([(80, 200), (150, 100), (220, 200)], fill=COLOR, width=LINE)


def draw_purl(draw):
    # purl: horizontal dash
    draw.line([(80, 150), (220, 150)], fill=COLOR, width=LINE)


def draw_yo(draw):
    draw.ellipse([(100, 100), (200, 200)], outline=COLOR, width=LINE)


def draw_slip(draw):
    # slip: diagonal slash
    draw.line([(80, 220), (220, 80)], fill=COLOR, width=LINE)


def draw_ktbl(draw):
    draw_knit(draw)
    draw.text((120, 210), "tbl", fill=COLOR, font=FONT)


def draw_ptbl(draw):
    draw_purl(draw)
    draw.text((120, 160), "tbl", fill=COLOR, font=FONT)


# ----------- 증가 ----------------

def draw_m1(draw):
    draw.text((130, 130), "M1", fill=COLOR, font=FONT)


def draw_m1l(draw):
    draw.line([(150, 80), (100, 220)], fill=COLOR, width=LINE)


def draw_m1r(draw):
    draw.line([(150, 80), (200, 220)], fill=COLOR, width=LINE)


# ----------- 줄임 ----------------

def draw_k2tog(draw):
    # right leaning
    draw.line([(80, 220), (220, 80)], fill=COLOR, width=LINE)


def draw_ssk(draw):
    # left leaning
    draw.line([(80, 80), (220, 220)], fill=COLOR, width=LINE)


def draw_p2tog(draw):
    draw_purl(draw)
    draw.text((130, 130), "2tog", fill=COLOR, font=FONT)


def draw_k3tog(draw):
    draw.line([(80, 220), (220, 80)], fill=COLOR, width=LINE)
    draw.text((130, 130), "3", fill=COLOR, font=FONT)


# ----------- 케이블 ----------------

def draw_cable_lc(draw, left, right):
    # 좌교차 케이블
    draw.line([(80, 200), (220, 100)], fill=COLOR, width=LINE)
    draw.line([(80, 100), (220, 200)], fill=COLOR, width=LINE)
    draw.text((130, 130), f"{left}/{right} LC", fill=COLOR, font=FONT)


def draw_cable_rc(draw, left, right):
    # 우교차 케이블
    draw.line([(80, 200), (220, 100)], fill=COLOR, width=LINE)
    draw.line([(80, 100), (220, 200)], fill=COLOR, width=LINE)
    draw.text((130, 130), f"{left}/{right} RC", fill=COLOR, font=FONT)


# ---------------- 생성 스케줄 ----------------

GENERATORS = {
    "k": draw_knit,
    "p": draw_purl,
    "yo": draw_yo,
    "sl": draw_slip,
    "ktbl": draw_ktbl,
    "ptbl": draw_ptbl,
    "k2tog": draw_k2tog,
    "k3tog": draw_k3tog,
    "ssk": draw_ssk,
    "p2tog": draw_p2tog,
    "m1": draw_m1,
    "m1l": draw_m1l,
    "m1r": draw_m1r,

    # 케이블 → 개별적 처리
}

# 케이블 목록 (당신이 보내준 리스트 기반)
CABLE_LIST = [
    ("1/1 LC", 1, 1, "LC"),
    ("1/1 RC", 1, 1, "RC"),
    ("2/2 LC", 2, 2, "LC"),
    ("2/2 RC", 2, 2, "RC"),
]


def generate_all():
    # 기본 스티치 생성
    for name, func in GENERATORS.items():
        save_icon(name, func)

    # 케이블 생성
    for key, L, R, typ in CABLE_LIST:
        if typ == "LC":
            save_icon(key.replace(" ", "_"), lambda d, L=L, R=R: draw_cable_lc(d, L, R))
        else:
            save_icon(key.replace(" ", "_"), lambda d, L=L, R=R: draw_cable_rc(d, L, R))

    print(f"✓ 모든 차트 기호 생성 완료 → {OUT_DIR}")


if __name__ == "__main__":
    generate_all()