# lib/gen_chart_images_v3.py
"""
뜨개 약어 사전에 있는 '차트로 표현 가능한 용어들'에 대해
국제표준 스타일 느낌의 차트 기호 PNG를 자동 생성하는 스크립트.

특히 케이블(교차뜨기)은
- 오른쪽 교차(RC): 오른쪽으로 기울어진 실이 '앞'에 오도록
- 왼쪽 교차(LC): 왼쪽으로 기울어진 실이 '앞'에 오도록
레이어 순서를 조절해 그립니다.

생성 위치: assets/chart/*.png

실행 방법:
    cd /workspaces/Silmari-knit_with_me
    python lib/gen_chart_images_v3.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 출력 폴더
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "chart"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 이미지 기본 설정
W, H = 300, 300
LINE = 10              # 기본 선 굵기
COLOR = "black"
BG = "white"

# 폰트
def _load_fonts():
    try:
        big = ImageFont.truetype("arial.ttf", 60)
        small = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        big = ImageFont.load_default()
        small = ImageFont.load_default()
    return big, small

FONT_BIG, FONT_SMALL = _load_fonts()


def slugify(s: str) -> str:
    s = s.strip()
    s = s.replace(" ", "_").replace("/", "_")
    s = "".join(ch for ch in s if ch.isalnum() or ch in "_-")
    return s or "symbol"


def get_text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_border(draw: ImageDraw.ImageDraw):
    m = 12
    draw.rectangle((m, m, W - m, H - m), outline="gray", width=3)


def save_icon(key: str, drawer):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_border(d)
    drawer(d)
    fname = slugify(key) + ".png"
    img.save(OUT_DIR / fname)
    return fname


# ------------------ 기본 스티치 ------------------ #

def knit(d: ImageDraw.ImageDraw):
    # 겉뜨기: V 모양
    d.line((W * 0.35, H * 0.7, W * 0.5, H * 0.3), fill=COLOR, width=LINE)
    d.line((W * 0.5, H * 0.3, W * 0.65, H * 0.7), fill=COLOR, width=LINE)


def purl(d: ImageDraw.ImageDraw):
    # 안뜨기: 가로선
    y = H * 0.5
    d.line((W * 0.3, y, W * 0.7, y), fill=COLOR, width=LINE)


def yo(d: ImageDraw.ImageDraw):
    # YO: 원형
    r = W * 0.18
    cx, cy = W * 0.5, H * 0.5
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=COLOR, width=LINE)


def slip(d: ImageDraw.ImageDraw):
    # 걸러뜨기: 대각선 슬래시
    d.line((W * 0.35, H * 0.7, W * 0.65, H * 0.3), fill=COLOR, width=LINE)


def ktbl(d: ImageDraw.ImageDraw):
    knit(d)
    txt = "tbl"
    w, h = get_text_size(d, txt, FONT_SMALL)
    d.text(((W - w) / 2, H * 0.75), txt, fill=COLOR, font=FONT_SMALL)


def ptbl(d: ImageDraw.ImageDraw):
    purl(d)
    txt = "tbl"
    w, h = get_text_size(d, txt, FONT_SMALL)
    d.text(((W - w) / 2, H * 0.6), txt, fill=COLOR, font=FONT_SMALL)


def kwise(d: ImageDraw.ImageDraw):
    # 겉뜨기 방향: V + 왼쪽에서 들어오는 화살표
    knit(d)
    d.polygon(
        (W * 0.25, H * 0.5, W * 0.33, H * 0.45, W * 0.33, H * 0.55),
        outline=COLOR,
        fill=None,
    )


def pwise(d: ImageDraw.ImageDraw):
    # 안뜨기 방향: ― + 왼쪽에서 들어오는 화살표
    purl(d)
    d.polygon(
        (W * 0.25, H * 0.5, W * 0.33, H * 0.45, W * 0.33, H * 0.55),
        outline=COLOR,
        fill=None,
    )


# ------------------ 증가 ------------------ #

def m1(d: ImageDraw.ImageDraw):
    yo(d)
    txt = "M1"
    w, h = get_text_size(d, txt, FONT_SMALL)
    d.text(((W - w) / 2, H * 0.76), txt, fill=COLOR, font=FONT_SMALL)


def m1l(d: ImageDraw.ImageDraw):
    # 왼기울임 증가: 왼쪽으로 열리는 V
    d.line((W * 0.45, H * 0.3, W * 0.35, H * 0.7), fill=COLOR, width=LINE)
    d.line((W * 0.55, H * 0.3, W * 0.65, H * 0.7), fill=COLOR, width=LINE)


def m1r(d: ImageDraw.ImageDraw):
    # 오른기울임 증가
    d.line((W * 0.35, H * 0.3, W * 0.45, H * 0.7), fill=COLOR, width=LINE)
    d.line((W * 0.65, H * 0.3, W * 0.55, H * 0.7), fill=COLOR, width=LINE)


def inc(d: ImageDraw.ImageDraw):
    yo(d)
    txt = "inc"
    w, h = get_text_size(d, txt, FONT_SMALL)
    d.text(((W - w) / 2, H * 0.76), txt, fill=COLOR, font=FONT_SMALL)


def german_short_row(d: ImageDraw.ImageDraw):
    # 독일식 경사뜨기: W 모양
    txt = "W"
    w, h = get_text_size(d, txt, FONT_BIG)
    d.text(((W - w) / 2, (H - h) / 2), txt, fill=COLOR, font=FONT_BIG)


def norwegian_cast_on(d: ImageDraw.ImageDraw):
    # 옛 노르웨이식 코잡기: CO
    txt = "CO"
    w, h = get_text_size(d, txt, FONT_BIG)
    d.text(((W - w) / 2, (H - h) / 2), txt, fill=COLOR, font=FONT_BIG)


# ------------------ 줄임 ------------------ #

def k2tog(d: ImageDraw.ImageDraw):
    # 오른기울임 줄임
    d.line((W * 0.35, H * 0.7, W * 0.65, H * 0.3), fill=COLOR, width=LINE)


def k3tog(d: ImageDraw.ImageDraw):
    # 3코 모아뜨기: V 두 개 겹친 느낌
    d.line((W * 0.25, H * 0.7, W * 0.5, H * 0.3), fill=COLOR, width=LINE)
    d.line((W * 0.75, H * 0.7, W * 0.5, H * 0.3), fill=COLOR, width=LINE)


def p2tog(d: ImageDraw.ImageDraw):
    purl(d)
    txt = "2tog"
    w, h = get_text_size(d, txt, FONT_SMALL)
    d.text(((W - w) / 2, H * 0.62), txt, fill=COLOR, font=FONT_SMALL)


def ssk(d: ImageDraw.ImageDraw):
    # 왼기울임 줄임
    d.line((W * 0.35, H * 0.3, W * 0.65, H * 0.7), fill=COLOR, width=LINE)


def ssp(d: ImageDraw.ImageDraw):
    # 왼기울임 안뜨기 줄임
    ssk(d)
    purl(d)


def tog(d: ImageDraw.ImageDraw):
    # generic tog
    d.line((W * 0.35, H * 0.7, W * 0.65, H * 0.3), fill=COLOR, width=LINE)
    txt = "tog"
    w, h = get_text_size(d, txt, FONT_SMALL)
    d.text(((W - w) / 2, H * 0.76), txt, fill=COLOR, font=FONT_SMALL)


# ------------------ 케이블: 앞/뒤가 구분되게 레이어링 ------------------ #

def cable_pair_rc(d: ImageDraw.ImageDraw):
    """
    오른쪽 교차(RC)
    - 뒤에 있는 실: \ 방향 (먼저 그림)
    - 앞에 있는 실: / 방향 (나중에 그림)
    """
    # 뒤 실 (\)
    d.line((W * 0.3, H * 0.3, W * 0.7, H * 0.7), fill="dimgray", width=LINE)

    # 앞 실 (/)
    d.line((W * 0.3, H * 0.7, W * 0.7, H * 0.3), fill=COLOR, width=LINE + 2)


def cable_pair_lc(d: ImageDraw.ImageDraw):
    """
    왼쪽 교차(LC)
    - 뒤에 있는 실: / 방향 (먼저 그림)
    - 앞에 있는 실: \ 방향 (나중에 그림)
    """
    # 뒤 실 (/)
    d.line((W * 0.3, H * 0.7, W * 0.7, H * 0.3), fill="dimgray", width=LINE)

    # 앞 실 (\)
    d.line((W * 0.3, H * 0.3, W * 0.7, H * 0.7), fill=COLOR, width=LINE + 2)


def cable_rc_label(d: ImageDraw.ImageDraw, label: str):
    cable_pair_rc(d)
    if label:
        w, h = get_text_size(d, label, FONT_SMALL)
        d.text(((W - w) / 2, H * 0.78), label, fill=COLOR, font=FONT_SMALL)


def cable_lc_label(d: ImageDraw.ImageDraw, label: str):
    cable_pair_lc(d)
    if label:
        w, h = get_text_size(d, label, FONT_SMALL)
        d.text(((W - w) / 2, H * 0.78), label, fill=COLOR, font=FONT_SMALL)


# ------------------ 매핑: 약어/용어 → 그리기 함수 ------------------ #

DRAW_MAP = {
    # 기본
    "k": knit,
    "p": purl,
    "yo": yo,
    "sl": slip,
    "ktbl": ktbl,
    "ptbl": ptbl,
    "kwise": kwise,
    "pwise": pwise,

    # 증가
    "M1": m1,
    "M1L": m1l,
    "M1R": m1r,
    "Inc": inc,
    "독일식 경사뜨기": german_short_row,
    "옛 노르웨이식 코잡기": norwegian_cast_on,

    # 줄임
    "k2tog": k2tog,
    "Knit 3 stitches together (k3tog)": k3tog,
    "p2tog": p2tog,
    "SSK": ssk,
    "SSP": ssp,
    "Tog": tog,

    # 케이블 (약어)
    "1/1 RC": lambda d: cable_rc_label(d, "1/1"),
    "1/1 LC": lambda d: cable_lc_label(d, "1/1"),
    "2/2 RC": lambda d: cable_rc_label(d, "2/2"),
    "2/2 LC": lambda d: cable_lc_label(d, "2/2"),

    # 케이블 (한글 설명형) – 오른쪽 교차
    "오른코 위 2코와 1코 교차뜨기": lambda d: cable_rc_label(d, "2+1"),
    "오른코 위 2코와 1코(안뜨기) 교차뜨기": lambda d: cable_rc_label(d, "2+1P"),
    "오른코 위 3코 교차뜨기": lambda d: cable_rc_label(d, "3"),
    "오른코 위 3코와 1코(안뜨기) 교차뜨기": lambda d: cable_rc_label(d, "3+1P"),
    "오른코에 꿴 매듭뜨기 (3코)": lambda d: cable_rc_label(d, "bobble"),

    # 케이블 (한글 설명형) – 왼쪽 교차
    "왼코 위 2코와 1코 교차뜨기": lambda d: cable_lc_label(d, "2+1"),
    "왼코 위 2코와 1코(안뜨기) 교차뜨기": lambda d: cable_lc_label(d, "2+1P"),
    "왼코 위 3코 교차뜨기": lambda d: cable_lc_label(d, "3"),
    "왼코 위 3코와 1코(안뜨기) 교차뜨기": lambda d: cable_lc_label(d, "3+1P"),

    # 한글 '걸러뜨기'
    "걸러뜨기": slip,
}


def main():
    print(f"출력 폴더: {OUT_DIR}")
    count = 0
    for key, drawer in DRAW_MAP.items():
        fname = save_icon(key, drawer)
        print(f"  - {key} → {fname}")
        count += 1
    print(f"\n✅ 총 {count}개의 차트 아이콘 생성 완료")


if __name__ == "__main__":
    main()