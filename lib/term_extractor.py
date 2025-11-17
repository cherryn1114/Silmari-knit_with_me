# lib/term_extractor.py
# 영상 제목(문자열)에서 뜨개 약어/용어만 뽑아주는 모듈

import re
from typing import List

# 1) 고정 약어 / 용어 패턴 → 표준 이름으로 매핑
#   - 왼쪽: 정규식
#   - 오른쪽: 우리가 쓰고 싶은 표준 키(약어/용어)
FIXED_PATTERNS = [
    # 증가/감소 계열
    (r"\bk2tog\b", "k2tog"),
    (r"\bp2tog\b", "p2tog"),
    (r"\bssk\b",   "ssk"),
    (r"\bskp\b",   "ssk"),      # skp 라고 적힌 것도 ssk로 통일
    (r"\bssp\b",   "ssp"),
    (r"\bm1l\b",   "m1L"),
    (r"\bm1 r\b",  "m1R"),
    (r"\bm1r\b",   "m1R"),
    (r"\bm1\b",    "M1"),
    (r"\binc\b",   "Inc"),
    (r"\bdec\b",   "Dec"),

    # YO / 꼬아뜨기
    (r"\byo\b",              "YO"),
    (r"\byarn\s*over\b",     "YO"),
    (r"\bktbl\b",            "ktbl"),
    (r"\bptbl\b",            "ptbl"),
    (r"\btbl\b",             "tbl"),

    # 시작/마무리
    (r"\bcast\s*on\b",       "CO"),
    (r"\bco\b",              "CO"),
    (r"\bcast\s*off\b",      "Cast off"),
    (r"\bbind\s*off\b",      "BO"),
    (r"\bbo\b",              "BO"),
    (r"\bpick\s*up\b",       "PU"),

    # 교차/케이블
    (r"\brc\b",              "RC"),
    (r"\bright\s*cross\b",   "RC"),
    (r"\blc\b",              "LC"),
    (r"\bleft\s*cross\b",    "LC"),
    (r"\bcable\b",           "Cable"),

    # 기본 조직
    (r"\bgarter\b",          "G-st"),
    (r"\b(st\s*st|stockinette|stocking\s*stitch)\b", "St-st"),
    (r"\bmoss\s*st(itch)?\b", "Moss st"),
    (r"\brib(bing)?\b",      "Rib"),

    # 방향/실 위치
    (r"\bwyif\b",            "YF"),
    (r"\bwyib\b",            "YB"),
    (r"\byarn\s*in\s*front\b", "YF"),
    (r"\byarn\s*in\s*back\b",  "YB"),

    # 마커, 기타
    (r"\bpm\b",              "PM"),
    (r"\bsm\b",              "SM"),
    (r"\bgauge\b",           "Gauge"),
    (r"\bdpn(s)?\b",         "dpn"),
]

# 2) 숫자/조합 패턴 (1x1 rib, 2x2 rib, 2/2 RC 등)
RIB_RE   = re.compile(r"\b(1\s*[x×]\s*1|2\s*[x×]\s*2)\s*(rib|r-?st)\b", re.I)
CROSS_RE = re.compile(r"\b(\d+\s*/\s*\d+)\s*(rc|lc)\b", re.I)

def extract_terms(title: str) -> List[str]:
    """
    영상 제목 문자열에서 뜨개 약어/용어만 뽑아서
    표준화된 리스트로 반환.
    예) "How to knit 1x1 rib & k2tog" → ["1x1 Rib", "k2tog"]
    """
    if not title:
        return []

    t = title.lower()
    found = set()

    # 1) 고정 패턴들 먼저 검사
    for pattern, name in FIXED_PATTERNS:
        if re.search(pattern, t, re.I):
            found.add(name)

    # 2) 1x1 / 2x2 rib 패턴
    m = RIB_RE.search(t)
    if m:
        num = m.group(1)
        # 공백 제거 + x 통일
        num_norm = re.sub(r"\s*", "", num).lower().replace("×", "x")
        if num_norm == "1x1":
            found.add("1x1 Rib")
        elif num_norm == "2x2":
            found.add("2x2 Rib")

    # 3) 2/2 RC / 2/1 LC 등 교차 패턴
    m = CROSS_RE.search(t)
    if m:
        frac = re.sub(r"\s*", "", m.group(1))  # "2/2"
        side = m.group(2).upper()              # RC/LC
        found.add(f"{frac} {side}")

    # 4) 너무 일반적인 단어(k, p 등)는 여기서는 제외 (원하면 추가 가능)
    #   예: "K" / "P"를 뽑고 싶다면 아래 주석을 응용하면 됨.

    return sorted(found)