# lib/gen_chart_images.py
# B 스타일: 네 PDF 도안처럼 굵은 대각선 + 앞/뒤가 보이는 차트 기호 생성기
#
# 사용법 (터미널):
#   cd /workspaces/Silmari-knit_with_me
#   python lib/gen_chart_images.py
#
# 결과:
#   assets/chart_icons/*.png  로 기호 아이콘 생성

from pathlib import Path
from typing import Dict
from PIL import Image, ImageDraw

W, H = 260, 260
BG = "white"
BORDER = "#999999"
LINE = "black"


def slug(key: str) -> str:
    """기호 이름을 파일 이름으로 바꾸기."""
    import re

    s = key.strip()
    s = s.replace(" ", "_").replace("/", "_").replace("\\", "_")
    s = s.replace("(", "").replace(")", "").replace(",", "")
    s = s.replace("+", "_")
    s = re.sub(r"[^0-9A-Za-z_가-힣]", "", s)
    return s


def base_canvas() -> Image.Image:
    """흰 배경 + 회색 테두리 캔버스."""
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([2, 2, W - 3, H - 3], outline=BORDER, width=4)
    return im


# ───────────────── 기본 스티치 / 기호 ─────────────────


def draw_knit(draw: ImageDraw.ImageDraw):
    # 일본식/국제 기호: 빈 사각형 느낌 (여기서는 중앙 세로 막대)
    cx = W // 2
    draw.line((cx, 40, cx, H - 40), fill=LINE, width=20)


def draw_purl(draw: ImageDraw.ImageDraw):
    # 안뜨기: 가운데 점 3개 (간단 점 기호)
    for dx in (-30, 0, 30):
        draw.ellipse(
            (W // 2 + dx - 10, H // 2 - 10, W // 2 + dx + 10, H // 2 + 10),
            fill=LINE,
            outline=LINE,
        )


def draw_slip_v(draw: ImageDraw.ImageDraw):
    # slip / s1 : V 모양 기호
    cx, cy = W // 2, H // 2
    size = 70
    draw.line(
        (cx - size, cy - size, cx, cy + size),
        fill=LINE,
        width=14,
    )
    draw.line(
        (cx + size, cy - size, cx, cy + size),
        fill=LINE,
        width=14,
    )


def draw_yo(draw: ImageDraw.ImageDraw):
    # Yarn over: 원형
    m = 55
    draw.ellipse((m, m, W - m, H - m), outline=LINE, width=14)


def draw_dec_slash(draw, left_leaning: bool, wide: bool = False, purl: bool = False):
    """
    줄임(모아뜨기) 기호: 대각선 하나 + (필요하면) 안뜨기 점.
    - left_leaning: True → ↙  (SSK 계열), False → ↘ (k2tog 계열)
    - wide: k3tog 처럼 굵게
    - purl: p2tog / SSP → 안뜨기 점 추가
    """
    m = 40
    if left_leaning:  # ↙
        p1 = (W - m, m)
        p2 = (m, H - m)
    else:  # ↘
        p1 = (m, m)
        p2 = (W - m, H - m)

    width = 14 if not wide else 20
    draw.line([p1, p2], fill=LINE, width=width)

    if purl:
        # 중앙에 점 1개
        draw.ellipse(
            (W // 2 - 14, H // 2 - 14, W // 2 + 14, H // 2 + 14),
            fill=BG,
            outline=LINE,
            width=8,
        )


def draw_inc_m1(draw, left: bool):
    """
    M1L / M1R: 사선 아래 작은 점 기호 스타일
    """
    bottom = H - 45
    top = 45
    if left:
        # 왼쪽 기울기 (M1L)
        draw.line(
            (W * 0.75, top, W * 0.25, bottom),
            fill=LINE,
            width=14,
        )
        x = int(W * 0.25)
    else:
        # 오른쪽 기울기 (M1R)
        draw.line(
            (W * 0.25, top, W * 0.75, bottom),
            fill=LINE,
            width=14,
        )
        x = int(W * 0.75)

    draw.ellipse(
        (x - 14, bottom - 14, x + 14, bottom + 14),
        fill=BG,
        outline=LINE,
        width=8,
    )


# ───────────────── 케이블 기호 (B 스타일) ─────────────────


def _draw_small_diag(draw, center, angle: str, length=40, width=10):
    """
    메인 케이블 주변의 '코 개수 표시용' 짧은 대각선.
    angle: 'L' or 'R'
    """
    cx, cy = center
    if angle == "L":  # /
        p1 = (cx - length // 2, cy + length // 2)
        p2 = (cx + length // 2, cy - length // 2)
    else:  # \
        p1 = (cx - length // 2, cy - length // 2)
        p2 = (cx + length // 2, cy + length // 2)

    draw.line([p1, p2], fill=LINE, width=width)


def draw_cable(draw, left_cnt: int, right_cnt: int, direction: str):
    """
    케이블 기호.
    - direction: 'L' (왼쪽으로 기울어짐, 왼쪽 다발이 앞) /
                 'R' (오른쪽으로 기울어짐, 오른쪽 다발이 앞)
    - left_cnt / right_cnt: 각측 코 개수 (1~3)
    B 스타일: 메인 굵은 대각선 + 양옆에 짧은 대각선 여러 개
    """
    margin = 40
    back_width = 14
    front_width = 22

    if direction == "L":
        # 왼쪽으로 기울어진 케이블 (앞 = 왼쪽 다발)
        back_main = [(margin, margin), (W - margin, H - margin)]
        front_main = [(W - margin, margin), (margin, H - margin)]
        angle_for_legs = "R"  # 짧은 선 각도
    else:
        # 오른쪽으로 기울어진 케이블 (앞 = 오른쪽 다발)
        back_main = [(W - margin, margin), (margin, H - margin)]
        front_main = [(margin, margin), (W - margin, H - margin)]
        angle_for_legs = "L"

    # 뒤줄 먼저 그리기 → 앞줄 나중
    draw.line(back_main, fill=LINE, width=back_width)
    draw.line(front_main, fill=LINE, width=front_width)

    # 양쪽 다발의 코 개수 표현 (짧은 대각선 여러 개)
    def draw_leg_group(x_center: int, top: bool, count: int):
        if count <= 0:
            return
        gap = 24
        start = - (count - 1) * gap / 2
        y = 70 if top else H - 70
        for i in range(count):
            cx = int(x_center + start + i * gap)
            _draw_small_diag(
                draw,
                (cx, y),
                angle_for_legs,
                length=30,
                width=10,
            )

    # 왼쪽 다발
    draw_leg_group(int(W * 0.28), True, left_cnt)
    draw_leg_group(int(W * 0.28), False, left_cnt)
    # 오른쪽 다발
    draw_leg_group(int(W * 0.72), True, right_cnt)
    draw_leg_group(int(W * 0.72), False, right_cnt)


# ───────────────── 어떤 기호를 어떤 모양으로 그릴지 매핑 ─────────────────

# symbols.json / symbols_extra.json 안의 "key"와 맞춰야 함
CHART_SPEC: Dict[str, Dict] = {
    # 1) 기본 스티치
    "k": {"kind": "knit"},
    "p": {"kind": "purl"},
    "yo": {"kind": "yo"},
    "sl": {"kind": "slip"},
    "s1": {"kind": "slip"},
    "걸러뜨기": {"kind": "slip"},

    # 2) 줄임 / 모아뜨기
    "k2tog": {"kind": "dec", "left": False, "purl": False},
    "p2tog": {"kind": "dec", "left": False, "purl": True},
    "Knit 3 stitches together (k3tog)": {"kind": "dec", "left": False, "purl": False, "wide": True},
    "k3tog": {"kind": "dec", "left": False, "purl": False, "wide": True},
    "SSK": {"kind": "dec", "left": True, "purl": False},
    "SSP": {"kind": "dec", "left": True, "purl": True},
    "SKPO": {"kind": "dec", "left": True, "purl": False},
    "SKP": {"kind": "dec", "left": True, "purl": False},

    # 3) M1L / M1R 만 (Inc, M1, Tog 등은 차트 세트에서 제외)
    "M1L": {"kind": "m1", "left": True},
    "M1R": {"kind": "m1", "left": False},

    # 4) 케이블 - 영어 약어
    "1/1 LC": {"kind": "cable", "L": 1, "R": 1, "dir": "L"},
    "1/1 RC": {"kind": "cable", "L": 1, "R": 1, "dir": "R"},
    "2/2 LC": {"kind": "cable", "L": 2, "R": 2, "dir": "L"},
    "2/2 RC": {"kind": "cable", "L": 2, "R": 2, "dir": "R"},
    "2/1 LPC": {"kind": "cable", "L": 2, "R": 1, "dir": "L"},
    "2/1 RPC": {"kind": "cable", "L": 2, "R": 1, "dir": "R"},
    "1/2 LPC": {"kind": "cable", "L": 1, "R": 2, "dir": "L"},
    "1/2 RPC": {"kind": "cable", "L": 1, "R": 2, "dir": "R"},

    # 5) 케이블 - 한글 설명 키(네 symbols_extra.json 쪽)
    "오른코 위 2코와 1코 교차뜨기": {"kind": "cable", "L": 2, "R": 1, "dir": "R"},
    "오른코 위 2코와 1코(안뜨기) 교차뜨기": {"kind": "cable", "L": 2, "R": 1, "dir": "R"},
    "오른코 위 3코 교차뜨기": {"kind": "cable", "L": 3, "R": 0, "dir": "R"},
    "오른코 위 3코와 1코(안뜨기) 교차뜨기": {"kind": "cable", "L": 3, "R": 1, "dir": "R"},
    "왼코 위 2코와 1코 교차뜨기": {"kind": "cable", "L": 2, "R": 1, "dir": "L"},
    "왼코 위 2코와 1코(안뜨기) 교차뜨기": {"kind": "cable", "L": 2, "R": 1, "dir": "L"},
    "왼코 위 3코 교차뜨기": {"kind": "cable", "L": 3, "R": 0, "dir": "L"},
    "왼코 위 3코와 1코(안뜨기) 교차뜨기": {"kind": "cable", "L": 3, "R": 1, "dir": "L"},
}


def render_icon(key: str) -> Image.Image:
    spec = CHART_SPEC[key]
    im = base_canvas()
    d = ImageDraw.Draw(im)

    kind = spec["kind"]

    if kind == "knit":
        draw_knit(d)
    elif kind == "purl":
        draw_purl(d)
    elif kind == "slip":
        draw_slip_v(d)
    elif kind == "yo":
        draw_yo(d)
    elif kind == "dec":
        draw_dec_slash(
            d,
            left_leaning=spec.get("left", False),
            wide=spec.get("wide", False),
            purl=spec.get("purl", False),
        )
    elif kind == "m1":
        draw_inc_m1(d, left=spec.get("left", True))
    elif kind == "cable":
        draw_cable(
            d,
            left_cnt=spec.get("L", 2),
            right_cnt=spec.get("R", 2),
            direction=spec.get("dir", "L"),
        )
    else:
        # 예상치 못한 kind → 겉뜨기와 같은 기본 기호로
        draw_knit(d)

    return im


def main():
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "assets" / "chart_icons"
    out_dir.mkdir(parents=True, exist_ok=True)

    for key in CHART_SPEC.keys():
        im = render_icon(key)
        fname = slug(key) + ".png"
        out_path = out_dir / fname
        im.save(out_path, format="PNG")
        print(f"✔ 생성: {out_path.relative_to(root)}")


if __name__ == "__main__":
    main()