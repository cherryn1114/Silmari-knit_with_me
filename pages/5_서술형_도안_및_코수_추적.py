# pages/5_서술형_도안_및_코수_추적.py

import streamlit as st
import re
from collections import defaultdict

from lib.pdf_utils import extract_pdf_text
from lib.upload_utils import uploader_with_history

st.set_page_config(
    page_title="실마리 — 서술형 도안 & 코수 추적",
    page_icon="📘",
    layout="wide",
)

st.title("📘 서술형 도안 & 코수 추적")

st.markdown(
    """
서술형 도안(PDF)에서 텍스트를 추출해서 **복사·붙여넣기** 하고,  
각 단계에서 **코 수가 어떻게 변하는지** 계산해 보는 페이지입니다.

1. PDF 도안을 업로드해서 텍스트를 추출하고,  
2. 필요한 줄(예: `k55, m1L`)을 복사해서 아래 코수 계산기에 붙여 넣으세요.
"""
)

# -------------------------------------------------------------------
# 1. PDF 업로드 & 텍스트 추출
# -------------------------------------------------------------------

st.header("1️⃣ PDF에서 도안 텍스트 추출하기")

# 세션 상태 기본값
if "pattern_text" not in st.session_state:
    st.session_state["pattern_text"] = ""

col_upload, col_desc = st.columns([2, 1])

with col_upload:
    st.caption("▼ 서술형 도안 PDF를 올려 주세요.")
    pdf_path = uploader_with_history("📎 서술형 도안 PDF 업로드", "pattern_pdf", ["pdf"])

    if pdf_path:
        st.success(f"PDF 파일이 업로드되었습니다.\n\n`{pdf_path}`")

        if st.button("📄 PDF에서 텍스트 추출하기", type="primary"):
            try:
                text = extract_pdf_text(pdf_path) or ""
                if not text.strip():
                    st.warning("PDF에서 텍스트를 찾지 못했습니다. 이미지 형태의 도안일 수 있어요.")
                st.session_state["pattern_text"] = text
                st.success("텍스트를 추출했습니다. 아래에서 복사해서 사용하세요.")
            except Exception as e:
                st.error(f"PDF 텍스트 추출 중 오류가 발생했습니다: {e}")
    else:
        st.info("먼저 PDF 파일을 업로드하면 텍스트를 추출할 수 있어요.")

with col_desc:
    st.markdown(
        """
**사용 방법**

1. 도안 PDF를 올립니다.  
2. `📄 PDF에서 텍스트 추출하기` 버튼을 누릅니다.  
3. 아래 텍스트 박스에 추출된 도안이 나타나면,  
   계산하고 싶은 줄만 골라서 복사해서 사용하세요.
"""
    )

st.text_area(
    "📋 추출된 도안 텍스트 (복사해서 사용하세요)",
    value=st.session_state["pattern_text"],
    height=260,
    key="pattern_text_area",
)

st.markdown("---")

# -------------------------------------------------------------------
# 2. 코수 계산기
# -------------------------------------------------------------------

st.header("2️⃣ 서술형 도안 한 줄에서 코 수 계산하기")

st.markdown(
    """
예시)  
- 시작 코 수가 **56코**이고, 도안 줄이 `k55, m1L` 이라면  
  → 55코 뜨고 +1코 늘어나서 **최종 57코**가 됩니다.

> 한 줄씩 / 구간별로 잘라서 계산하면서 진행하면,  
> 전체 도안의 코 수 변화를 따라가기가 훨씬 편해져요.
"""
)

# 세션 기본값
if "stitch_start" not in st.session_state:
    st.session_state["stitch_start"] = 0

col_left, col_right = st.columns([1, 2])

with col_left:
    start_st = st.number_input(
        "현재(시작) 전체 코 수",
        min_value=0,
        step=1,
        value=st.session_state["stitch_start"],
        help="이 줄을 뜨기 직전에 가지고 있는 전체 코 수를 적어 주세요.",
    )
    st.session_state["stitch_start"] = start_st

with col_right:
    line_text = st.text_area(
        "계산할 도안 줄 / 구간 (예: `k55, m1L`)",
        height=120,
        placeholder="예) k55, m1L  또는  k2tog, yo, k2, m1R ...",
        key="stitch_line_text",
    )

st.caption("쉼표(,) 또는 공백 기준으로 나눠서 약어를 인식합니다. 소문자/대문자는 구분하지 않아요.")

# ---------------------- 계산 로직 ---------------------- #

def parse_stitch_ops(text: str):
    """
    간단한 서술형 도안 한 줄을 파싱해서
    - 코 수 증감량(delta)
    - 인식된 토큰 목록
    - 인식 못한 토큰 목록
    을 반환합니다.
    """
    if not text.strip():
        return 0, [], []

    # 소문자로 통일 & 한글 쉼표도 처리
    raw = text.replace("，", ",").replace("·", " ")
    raw = raw.lower()

    # 쉼표 / 개행 / 공백 기준으로 토큰 분리
    tokens = []
    for part in re.split(r"[,\n]", raw):
        part = part.strip()
        if not part:
            continue
        tokens.extend([t for t in part.split() if t])

    delta = 0
    parsed = []
    unknown = []

    # 증가/감소 규칙 정의 (아주 단순 버전)
    inc_one = {"yo", "m1", "m1l", "m1r", "inc", "kfb", "pfb"}
    dec_one = {"ssk", "ssp", "skpo"}

    for tok in tokens:
        t = tok.strip()

        # 1) k55, p10, sl3 등: 코 수는 그대로 (증감 0)
        m = re.match(r"^(k|p|sl)(\d+)$", t)
        if m:
            op, n = m.group(1), int(m.group(2))
            parsed.append((t, 0, f"{op}{n} : {n}코 뜨기 → 코 수 변동 없음"))
            continue

        # 2) k, p, sl 단독 → 1코 뜨기 (변동 없음)
        if t in {"k", "p", "sl"}:
            parsed.append((t, 0, f"{t} : 1코 뜨기 → 코 수 변동 없음"))
            continue

        # 3) yo, m1, m1l, m1r, inc, kfb, pfb → +1코
        if t in inc_one:
            delta += 1
            parsed.append((t, +1, f"{t} : 1코 늘리기 → +1코"))
            continue

        # 4) k2tog, k3tog, p2tog, p3tog 등: n코를 1코로 모아뜨기 → -(n-1)코
        m = re.match(r"^(k|p)(\d)tog$", t)
        if m:
            n = int(m.group(2))
            d = 1 - n  # 예: 2코 ⇒ -1, 3코 ⇒ -2
            delta += d
            parsed.append((t, d, f"{t} : {n}코를 1코로 모아뜨기 → {d:+}코"))
            continue

        # 5) ssk, ssp, skpo → 2코를 1코로 모아뜨기(-1코)로 처리
        if t in dec_one:
            delta -= 1
            parsed.append((t, -1, f"{t} : 2코를 1코로 모아뜨기 → -1코"))
            continue

        # 6) 숫자만 있는 경우 (예: '55') → 현재로서는 의미 모호 → 인식 못한 토큰 처리
        if re.fullmatch(r"\d+", t):
            unknown.append(t)
            continue

        # 이 외에는 일단 인식 못한 토큰으로 남겨둠
        unknown.append(t)

    return delta, parsed, unknown


result_placeholder = st.empty()

if st.button("🧮 이 줄 계산하기", type="primary"):
    delta, parsed_ops, unknown_ops = parse_stitch_ops(line_text)
    final_st = start_st + delta

    with result_placeholder.container():
        st.subheader("결과")

        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.metric("시작 코 수", start_st)
        with col_b:
            st.metric("이 줄 이후 코 수", final_st, delta=f"{delta:+} 코")

        if parsed_ops:
            st.markdown("#### 🔍 인식된 명령 해석")
            for tok, d, msg in parsed_ops:
                st.markdown(f"- **{tok}** → {msg}")

        if unknown_ops:
            st.markdown("#### ⚠ 인식하지 못한 토큰")
            st.write(
                ", ".join(sorted(set(unknown_ops)))
                + "\n\n이 부분은 직접 코 수 변화를 확인해서 반영해야 해요."
            )

        st.info(
            "다음 줄을 계산할 때는 **이 줄 이후 코 수**를 다시 \"현재(시작) 전체 코 수\"로 넣고 반복해서 계산하면 됩니다."
        )
else:
    result_placeholder.info("위에 도안 줄과 시작 코 수를 입력한 뒤 **[🧮 이 줄 계산하기]** 버튼을 눌러 주세요.")

st.markdown("---")
st.page_link("HOME.py", label="🏠 홈으로")