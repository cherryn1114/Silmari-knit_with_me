# lib/parser.py
# Python 3.8+ 호환 / 경로 안정성 / 정규식 보강 / 빈 입력·오타 대응 강화

import re
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from rapidfuzz import process, fuzz

# 전역 캐시
_LIB: Optional[Dict[str, Any]] = None
_ALL_KEYS: Optional[List[str]] = None
_LIB_PATH: Optional[Path] = None

def _resolve_path(p: str) -> Path:
    # 현재 파일 위치 기준 상대경로 -> 절대경로
    base = Path(__file__).resolve().parent
    return (base / p).resolve()

def load_lib(path: str) -> Dict[str, Any]:
    """
    symbols.json 로드 (최초 1회 캐싱)
    path: 'lib/symbols.json'처럼 상대경로로 넘겨도 됨
    """
    global _LIB, _ALL_KEYS, _LIB_PATH
    if _LIB is not None and _LIB_PATH is not None and _LIB_PATH == _resolve_path(path):
        return _LIB

    lib_path = _resolve_path(path)
    if not lib_path.exists():
        raise FileNotFoundError(f"symbols.json을 찾을 수 없습니다: {lib_path}")

    _LIB = json.loads(lib_path.read_text(encoding="utf-8"))
    _ALL_KEYS = list(_LIB.keys())
    # alias까지 포함해 퍼지 검색 품질 향상
    for v in _LIB.values():
        for a in v.get("aliases", []):
            if a not in _ALL_KEYS:
                _ALL_KEYS.append(a)
    _LIB_PATH = lib_path
    return _LIB

def find_term(q: str) -> Tuple[str, Dict[str, Any]]:
    """
    약어/동의어/오타(1~2자)까지 퍼지 매칭
    return: (표준키, 항목dict) / 없으면 ("", {})
    """
    global _LIB, _ALL_KEYS
    if not q or not q.strip():
        return "", {}
    if _LIB is None or _ALL_KEYS is None:
        raise RuntimeError("라이브러리가 아직 로드되지 않았습니다. load_lib() 먼저 호출하세요.")

    res = process.extractOne(q, _ALL_KEYS, scorer=fuzz.token_set_ratio)
    if not res:
        return "", {}
    match = res[0]

    # 표준 키로 바로 존재
    if match in _LIB:
        return match, _LIB[match]
    # alias -> 표준키 역매핑
    for k, v in _LIB.items():
        if match in v.get("aliases", []):
            return k, v
    return "", {}

# *...* n회 / [...] x n / k3 / p2 / 단일 토큰 / , ;
# 회, times, x, X, ×(유니코드) 모두 허용
TOKEN_RE = re.compile(r"""
    \*\s*(.*?)\s*\*\s*(\d+)\s*(?:회|times|[xX×])   |   # * ... * n회
    \[\s*(.*?)\s*\]\s*(\d+)\s*(?:회|times|[xX×])   |   # [ ... ] n회
    \b(k|p)\s*(\d+)\b                              |   # k3, p2
    \b(k2tog|p2tog|ssk|ssp|yo|m1L|m1R|k|p)\b       |   # 단일 토큰
    [,;]                                           |   # 구분자
""", re.VERBOSE | re.IGNORECASE)

def expand_sequence(s: str) -> List[str]:
    """
    서술형 문자열을 토큰 리스트로 전개
    예) "[(p, k) x 6, m1L] x 8" -> ["p","k","p","k",...,"m1l", ...] (소문자 표준화)
    """
    if not s:
        return []
    # 표준화: 한글 '회'는 그대로, 곱하기 ×, x, X 섞여도 처리
    s = s.replace("×", "x")
    tokens: List[str] = []
    idx = 0

    while idx < len(s):
        m = TOKEN_RE.search(s, idx)
        if not m:
            # 남은 문자열 쪼개기 (토큰성이 낮은 잔여는 무시)
            rest = s[idx:].strip()
            if rest:
                # 쉼표/세미콜론 제거 후 공백 분리
                rest = rest.strip(",;")
                parts = [p for p in re.split(r"\s+", rest) if p]
                tokens.extend(parts)
            break

        start, end = m.span()
        # 매치 이전의 느슨한 텍스트 처리 (콤마/세미콜론 제거)
        pre = s[idx:start].strip(" ,;")
        if pre:
            tokens.extend([p for p in re.split(r"\s+", pre) if p])

        g = m.groups()
        # 그룹 순서에 주의: 위 정규식의 각 케이스와 매칭
        if g[0] and g[1]:     # * ... * n회
            inner, n = g[0], int(g[1])
            inner_expanded = expand_sequence(inner)
            tokens.extend(inner_expanded * n)
        elif g[2] and g[3]:   # [ ... ] n회
            inner, n = g[2], int(g[3])
            inner_expanded = expand_sequence(inner)
            tokens.extend(inner_expanded * n)
        elif g[4] and g[5]:   # kN / pN
            base, num = g[4].lower(), int(g[5])
            tokens.extend([base] * num)
        elif g[6]:            # 단일 토큰
            tokens.append(g[6].lower())

        idx = end

    # 최종 정리: 콤마/세미콜론 제거 + 공백 제거
    tokens = [t.strip().strip(",;").lower() for t in tokens if t.strip() and t.strip() not in [",",";"]]
    return tokens

def stitch_delta(tok: str, lib: Dict[str, Any]) -> int:
    """
    토큰이 코수에 주는 변화량
    """
    if not tok:
        return 0
    key = tok.lower()

    # 기본 스티치
    if key in ("k", "p"):
        return 0

    # m1L/m1R 대소문자 이슈 보정
    lib_key = key.upper() if key.startswith("m1") else key
    if lib_key in lib:
        return int(lib[lib_key].get("delta", 0))

    # 백업 매핑
    mapping = {"yo": 1, "m1l": 1, "m1r": 1, "k2tog": -1, "p2tog": -1, "ssk": -1, "ssp": -1}
    return mapping.get(key, 0)

def compute_counts(tokens: List[str], start_sts: int, lib: Dict[str, Any]) -> List[Tuple[int, str, int, int]]:
    """
    각 스텝별 누적 기대 코수 계산
    반환: [(스텝, 토큰, 기대코수, Δ코수), ...]
    """
    cur = int(start_sts)
    out: List[Tuple[int, str, int, int]] = []
    step = 1
    for t in tokens:
        d = stitch_delta(t, lib)
        cur += d
        out.append((step, t, cur, d))
        step += 1
    return out

# (선택) 한 번에 요약까지 뽑는 편의 함수
def summarize(pattern: str, start_sts: int, lib_path: str) -> Dict[str, Any]:
    lib = load_lib(lib_path)
    toks = expand_sequence(pattern)
    rows = compute_counts(toks, start_sts, lib)
    end = rows[-1][2] if rows else start_sts
    return {"tokens": toks, "rows": rows, "expected_end": end}