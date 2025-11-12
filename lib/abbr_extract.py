# lib/abbr_extract.py
# 제목/문장에서 뜨개 약어 추출 + 표준키 후보 만들기

import re
from typing import List, Dict

# 1) 고정 약어 패턴 (대/소문자 무시)
FIXED = r"""
\b(
    k2tog|p2tog|ssk|ssp|skp|yo|
    m1l|m1r|m1|inc|dec|
    ktbl|ptbl|tbl|
    rc|lc|co|bo|pm|sm|rs|ws|dpn|
    st(?:-?st)?|g-st|g?arter|moss(?:\s*st)?|
    rib|r-?st|
    yf(?:wd)?|wyif|ybk|wyib|
    pu|sl|kwise|pwise|mc|cc
)\b
"""

# 2) 숫자/기호 조합 패턴
PATTERNS: Dict[str, str] = {
    # 1x1 rib / 2x2 rib
    "rib_xx": r"\b(\d+\s*[x×]\s*\d+)\s*(rib|r-?st)\b",
    # 2/2 RC / 2/1 LC
    "cross": r"\b(\d+\s*/\s*\d+)\s*(rc|lc)\b",
    # k3 / p5 (연속 겉/안)
    "kpN": r"\b(k|p)\s*(\d+)\b",
}

FIXED_RE = re.compile(FIXED, re.I | re.X)

def extract_abbr(text: str) -> List[str]:
    """
    title/문장에서 약어 리스트를 추출 (중복/대소문자 정리)
    """
    if not text:
        return []
    found = set()

    # 0) 미리 소문자/공백 정리
    t = re.sub(r"\s+", " ", text).strip()

    # 1) 고정 약어
    for m in FIXED_RE.finditer(t):
        found.add(m.group(1).lower())

    # 2) 1x1/2x2 rib
    m = re.search(PATTERNS["rib_xx"], t, re.I)
    if m:
        num = re.sub(r"\s+", "", m.group(1).lower())  # '1x1' 식
        found.add(f"{num} rib")

    # 3) 2/2 RC/LC
    m = re.search(PATTERNS["cross"], t, re.I)
    if m:
        frac = re.sub(r"\s+", "", m.group(1))  # '2/2'
        side = m.group(2).upper()              # RC/LC
        found.add(f"{frac} {side}")

    # 4) k3/p5 같은 연속 지시 → k,p 자체는 약어가 아니라서 별도 결과에 넣진 않음
    #    필요하면 'k3','p2' 같이 그대로 보고 싶을 때 주석 해제
    # for m in re.finditer(PATTERNS["kpN"], t, re.I):
    #     found.add(f"{m.group(1).lower()}{m.group(2)}")

    return sorted(found)

def guess_primary_key(abbrs: List[str], title: str) -> str:
    """
    추출된 약어들 중 '대표키' 후보를 하나 골라줌.
    규칙:
      1) k2tog/p2tog/ssk/ssp/m1l/m1r/yo 등 핵심 우선
      2) 1x1 rib / 2x2 rib / garter / stockinette 등 조직
      3) 2/2 RC/LC 같은 교차
      4) 없으면 제목 그대로
    """
    order = [
        "k2tog","p2tog","ssk","ssp","m1l","m1r","yo",
        "ktbl","ptbl","rc","lc","co","bo","pm","sm","dpn",
        "1x1 rib","2x2 rib","rib","garter","st-st","stockinette","moss st","g-st",
        "wyif","wyib","yfwd","ybk","mc","cc","pu","sl",
    ]
    s = set(abbrs)
    for k in order:
        if k in s:
            return k
    # 교차(2/2 RC) 같은 복합 키가 있으면 그중 하나
    if abbrs:
        return abbrs[0]
    return title.strip()