# lib/extract_chart_terms.py
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent / "symbols.json"
EXTRA = Path(__file__).resolve().parent / "symbols_extra.json"

def load(p):
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

base = load(BASE)
extra = load(EXTRA)
merged = {**base, **extra}

# 차트 가능 키워드 패턴
chart_keywords = [
    r"\bk\b", r"\bp\b", r"tbl", r"yo\b", r"sl\b",
    r"tog", r"ssk", r"ssp", r"dec", r"inc",
    r"m1", r"yo", r"rt\b", r"lt\b", r"twist",

    # cable
    r"\d+/\d+\s*rc", r"\d+/\d+\s*lc",
    r"\d+/\d+\s*rpc", r"\d+/\d+\s*lpc",
    r"\d+/\d+\s*cross",
]

compiled = [re.compile(p, re.IGNORECASE) for p in chart_keywords]

def is_chart_capable(key, item):
    txt = " ".join([
        key,
        item.get("name_en",""),
        item.get("name_ko",""),
        " ".join(item.get("aliases",[]))
    ]).lower()

    return any(p.search(txt) for p in compiled)

out = []

for key, item in merged.items():
    if is_chart_capable(key, item):
        out.append(key)

print("=== 차트 생성 가능 용어 목록 ===")
for k in sorted(out):
    print("-", k)

print(f"\n총 {len(out)}개")