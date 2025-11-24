# pages/5_서술형_도안_및_코수_추적.py

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from lib.upload_utils import uploader_with_history

# PDF 텍스트 추출용 (텍스트 기반 PDF만 지원, 이미지 스캔 PDF는 따로 텍스트 붙여넣어야 함)
try:
    import PyPDF2  # type: ignore
except ImportError:
    PyPDF2 = None


# -----------------------
# 기본 설정
# -----------------------
st.set_page_config(
    page_title="실마리 — 서술형 도안 + 코수 추적",
    page_icon="🧾",
    layout="centered",
)

st.title("🧾 서술형 도안 설명 + 코수 자동 추적")

st.markdown(
    """
서술형(글로 된) 도안을 PDF 또는 텍스트로 넣으면,  
각 단계(단/줄)별로 **코 수가 어떻게 변하는지** 대략적으로 추적해줍니다.

- PDF 업로드 → 텍스트 자동 추출 (텍스트 기반 PDF일 때)
- 이미지/스캔 PDF → 아래 텍스트 영역에 직접 복붙해서 사용
- 증가/감소 기호(k2tog, ssk, yo, 2코 모아뜨기 등)를 인식해서 **코 수 변화를 추정**합니다.
"""
)

st.divider()

# -----------------------
# 1) 도안 파일 업로드
# -----------------------

st.header("1️⃣ 도안 파일 업로드 (선택)")

st.caption(
    "텍스트 기반 PDF라면 이곳에 업로드하면 도안 내용이 자동으로 텍스트로 추출됩니다. "
    "이미지/스캔 PDF 또는 JPG/PNG는 **텍스트만 수동으로 복사해서 아래에 붙여넣어야** 합니다."
)

pattern_path: Path | None = uploader_with_history(
    label="PDF 또는 이미지 업로드",
    type=["pdf", "png", "jpg", "jpeg", "webp"],
    key="pattern_upload",
)

extracted_text = ""


def extract_text_from_pdf(path: Path) -> str:
    """PyPDF2로 단순 텍스트 추출 (텍스트 기반 PDF 전용)."""
    if PyPDF2 is None:
        return ""
    try:
        with path.open("rb") as f:
            reader = PyPDF2.PdfReader(f)
            texts = []
            for page in reader.pages:
                t = page.extract_text() or ""
                texts.append(t)
            return "\n\n".join(texts)
    except Exception:
        return ""


if pattern_path:
    st.success(f"📁 선택된 파일: `{pattern_path.name}`")

    if pattern_path.suffix.lower() == ".pdf":
        if PyPDF2 is None:
            st.warning(
                "PyPDF2 라이브러리가 설치되지 않아 PDF 텍스트를 자동 추출할 수 없습니다. "
                "터미널에서 `pip install PyPDF2` 후 다시 실행해주세요."
            )
        else:
            with st.spinner("PDF에서 텍스트를 추출하는 중입니다..."):
                extracted_text = extract_text_from_pdf(pattern_path)
            if extracted_text.strip():
                st.info("PDF에서 텍스트를 추출했습니다. 아래 텍스트 영역에서 내용을 확인/수정하세요.")
            else:
                st.warning(
                    "PDF에서 텍스트를 추출하지 못했습니다. "
                    "이미지 기반 PDF이거나 보호된 파일일 수 있습니다.\n\n"
                    "→ 도안 내용을 복사해서 아래 텍스트 영역에 직접 붙여넣어 주세요."
                )
    else:
        st.info(
            "이미지 파일은 자동 OCR을 지원하지 않습니다. "
            "이미지에서 도안 텍스트를 직접 읽어 아래 텍스트 영역에 붙여넣어 주세요."
        )
else:
    st.caption("도안 파일을 업로드하지 않고, 바로 텍스트만 붙여넣어도 됩니다.")

st.divider()

# -----------------------
# 2) 도안 텍스트 입력/편집
# -----------------------

st.header("2️⃣ 도안 텍스트 입력 / 편집")

default_hint = """예시)
CO 80 sts.
Row 1 (RS): *k2, p2* to end. (80 sts)
Row 2: purl.
Row 3: k2, (yo, k2tog) x 10, k to end.
Row 4: purl.
"""

pattern_text = st.text_area(
    "도안 설명이나 필요한 기술/약어 전체를 여기에 붙여넣으세요.",
    value=extracted_text.strip() or default_hint,
    height=260,
)


st.markdown(
    """
- 영어 도안: `k2tog`, `ssk`, `yo`, `m1`, `kfb`, `p2tog`, `k3tog` 등 증가/감소를 인식합니다.  
- 한글 도안: `2코 모아뜨기`, `3코 모아뜨기`, `한코 늘리기` 같은 표현도 일부 인식합니다.  
- 완벽히 정확하진 않지만, **대략적인 코 수 변화 흐름**을 확인하는 데 도움을 주는 도구입니다.
"""
)

st.divider()

# -----------------------
# 3) 초기 코 수 입력
# -----------------------

st.header("3️⃣ 시작 코 수 입력")

initial_sts = st.number_input(
    "처음 시작할 때 잡는 코 수 (CO 이후 총 코 수)",
    min_value=0,
    max_value=2000,
    value=80,
    step=1,
)


st.divider()

# -----------------------
# 4) 텍스트에서 줄(단) 추출 + 코 수 추적
# -----------------------

st.header("4️⃣ 줄/단 별 코 수 변화 추적")

st.caption("도안 텍스트에서 'Row 1', '1단', 'Step 1' 같은 줄 단위를 찾아 코 수 변화를 계산합니다.")


LINE_PATTERNS = [
    r"^\s*(row|rnd|round|step)\s*\d+[:\.]?\s*(.*)$",  # Row 1: ...
    r"^\s*(\d+)\s*(단|번째 단|줄)[:\.]?\s*(.*)$",       # 1단: ...
]


def split_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def detect_line_label_and_body(line: str) -> tuple[str, str]:
    # 1) 영어 Row 1, Round 2 등
    m = re.match(r"^\s*(Row|Rnd|Round|Step)\s*(\d+)\s*(\(.*?\))?[:\.]?\s*(.*)$", line, re.IGNORECASE)
    if m:
        label = f"{m.group(1)} {m.group(2)}"
        body = m.group(4) or ""
        return label, body or line

    # 2) 한글 1단, 2단, 3번째 단, 5줄 등
    m = re.match(r"^\s*(\d+)\s*(단|번째 단|줄)\s*[:\.]?\s*(.*)$", line)
    if m:
        label = f"{m.group(1)}{m.group(2)}"
        body = m.group(3) or ""
        return label, body or line

    # 3) 못 찾았으면 원문 전체를 label로
    return "", line


def estimate_delta(instr: str) -> int:
    """
    한 줄(단)의 설명에서 대략적인 코 수 변화량을 추정.
    +값: 증가, -값: 감소, 0: 변화 없음/알 수 없음.
    """
    s = instr.lower()
    inc = 0
    dec = 0

    # ---- 영어 감소 기호들 ----
    # k2tog, k3tog, k4tog ...
    for m in re.finditer(r"k(\d+)tog", s):
        n = int(m.group(1))
        dec += (n - 1)

    for m in re.finditer(r"p(\d+)tog", s):
        n = int(m.group(1))
        dec += (n - 1)

    # k2tog, p2tog 등 숫자 없는 기본형
    for pat in ["k2tog", "p2tog", "ssk", "ssp", "skp", "skpo", "k2tog tbl", "p2tog tbl"]:
        if pat in s:
            dec += s.count(pat)  # 개수만큼 -1

    # 2tog 라는 표현이 단독으로 있을 수도 있음
    for m in re.finditer(r"(\d+)tog", s):
        n = int(m.group(1))
        dec += (n - 1)

    # ---- 영어 증가 기호들 ----
    for pat in ["yo", "m1", "m1l", "m1r", "kfb", "pfb"]:
        if pat in s:
            inc += s.count(pat)

    # "yo twice" 같은 표현 (rough)
    if "yo twice" in s or "yo 2 times" in s:
        inc += 1  # 이미 yo 1회 세었을 테니 +1만 추가

    # ---- 한글 모아뜨기 (감소) ----
    # "3코 모아뜨기" → 2코 감소
    for m in re.finditer(r"(\d+)\s*코\s*모아뜨기", instr):
        n = int(m.group(1))
        dec += (n - 1)

    # ---- 한글 늘리기 (증가) ----
    # "한코 늘리기", "1코 늘리기"
    for m in re.finditer(r"(\d+)\s*코\s*(늘리기|늘려뜨기)", instr):
        n = int(m.group(1))
        inc += (n)

    if "한코 늘리기" in instr:
        inc += instr.count("한코 늘리기")

    return inc - dec


def analyze_pattern(text: str, start_sts: int) -> list[dict]:
    lines = split_lines(text)
    steps: list[dict] = []
    current_sts = start_sts

    for raw in lines:
        label, body = detect_line_label_and_body(raw)
        delta = estimate_delta(body)
        current_sts += delta
        steps.append(
            {
                "label": label or "(줄 구분 인식 안 됨)",
                "text": body if body else raw,
                "raw": raw,
                "delta": delta,
                "stitches_after": current_sts,
            }
        )
    return steps


if pattern_text.strip():
    steps = analyze_pattern(pattern_text, initial_sts)

    st.subheader("🔍 분석 결과 (줄/단 별 코 수 변화)")

    if not steps:
        st.info("분석할 줄을 찾지 못했습니다. 텍스트에 도안 설명을 더 넣어 보세요.")
    else:
        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "줄/단 이름": s["label"],
                    "설명": s["text"],
                    "코 수 변화(Δ)": s["delta"],
                    "현재 총 코 수": s["stitches_after"],
                }
                for s in steps
            ]
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        final_sts = steps[-1]["stitches_after"]
        st.markdown(
            f"""
**요약**

- 시작 코 수: **{initial_sts}코**
- 마지막 줄/단 이후 코 수: **{final_sts}코**
- 전체 줄/단 수: **{len(steps)}개**
"""
        )

        st.caption(
            "※ 이 계산은 도안 문장을 단순 규칙으로 분석한 *대략적인 추정치*입니다. "
            "특히 복잡한 반복구간(* * 안에 반복, 괄호 안 반복 등)은 실제 코 수와 다를 수 있으니, "
            "반드시 최종 도안을 직접 한 번 더 검산해 주세요."
        )
else:
    st.info("위 텍스트 영역에 도안 설명을 붙여넣으면, 여기에서 코 수 분석 결과가 표시됩니다.")

st.divider()
st.page_link("HOME.py", label="⬅️ 홈으로")