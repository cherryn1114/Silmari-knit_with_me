# pages/5_서술형_도안_및_코수_추적.py

import streamlit as st
import re
from typing import Dict, Tuple
from lib.upload_utils import uploader_with_history
from lib.pdf_utils import extract_pdf_text


# ---------------------------------------------------------
# Streamlit 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="서술형 도안 & 코 수 추적",
    page_icon="🧮",
    layout="wide"
)

st.title("🧶 서술형 도안 & 코 수 추적")

st.markdown("""
서술형 도안의 문장을 한 줄씩 넣으면 증가/감소 코 수를 계산해 주는 페이지입니다.

### 📌 계산 규칙 (기본)
- **k, p 등 단순 겉뜨기/안뜨기** → 코 수 변화 없음 (0)
- **yo, m1, m1l, m1r 등 늘리기** → +1 증가
- **k2tog, ssk, ssp, p2tog 등 2코 모아뜨기** → -1 감소
- **k3tog, p3tog 등 3코 모아뜨기** → -2 감소
- **반복 표현**  
  - “3회 반복”, “3번 반복”, “×3”, “3 times”, “\* ~ \* 반복” 모두 반복 횟수 적용
""")


# ============================================================
# 1️⃣ PDF에서 도안 텍스트 추출하기
# ============================================================
st.header("1️⃣ PDF에서 도안 텍스트 추출하기")

uploaded_file, saved_path = uploader_with_history(
    key="pattern_pdf",
    label="📄 서술형 도안 PDF 업로드",
    help_text="PDF 파일을 업로드한 후 텍스트를 추출하여 아래에 표시합니다."
)

if uploaded_file:
    st.success(f"PDF 파일이 업로드되었습니다: **{uploaded_file.name}**")

    if st.button("📕 PDF에서 텍스트 추출하기", type="primary"):
        try:
            text = extract_pdf_text(saved_path)
            st.success("텍스트를 성공적으로 추출했습니다. 아래에서 복사해 활용하세요.")
            st.text_area("📄 추출된 도안 텍스트", value=text, height=300)
        except Exception as e:
            st.error("❌ PDF 텍스트 추출 중 오류가 발생했습니다.")
            st.exception(e)



# ============================================================
# 2️⃣ 서술형 도안 한 줄에서 코 수 계산하기
# ============================================================

st.header("2️⃣ 서술형 도안 한 줄에서 코 수 계산하기")

start_sts = st.number_input("🔢 시작 코 수", min_value=0, value=56, step=1)
line_text = st.text_area("✏️ 도안 한 줄 입력", height=120)

# ------------------------------
# 코 수 변화 계산 규칙
# ------------------------------
INC_PATTERNS = ["yo", "m1l", "m1r", "yo."]
DEC1_PATTERNS = ["k2tog", "ssk", "ssp", "p2tog"]
DEC2_PATTERNS = ["k3tog", "p3tog"]

# 반복 패턴 인식
REPEAT_PATTERNS = [
    r"(\d+)\s*회\s*반복",      # 3회 반복
    r"(\d+)\s*번\s*반복",      # 3번 반복
    r"×\s*(\d+)",              # ×3
    r"x\s*(\d+)",              # x3
    r"(\d+)\s*times"           # 3 times
]


def count_st_changes(text: str) -> Tuple[int, Dict[str, int]]:
    """도안 한 줄의 총 증가/감소 코 수 계산"""

    delta = 0
    detail = {}

    # 1) 반복 횟수 찾기
    repeat = 1
    for pat in REPEAT_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            repeat = int(m.group(1))
            break

    # 2) 요소별 계산
    lowered = text.lower()

    # 증가 (+1)
    for inc in INC_PATTERNS:
        c = lowered.count(inc)
        if c:
            detail[inc] = c * repeat
            delta += c * repeat * 1

    # 2코 모아뜨기 (-1)
    for d in DEC1_PATTERNS:
        c = lowered.count(d)
        if c:
            detail[d] = c * repeat
            delta -= c * repeat * 1

    # 3코 모아뜨기 (-2)
    for d in DEC2_PATTERNS:
        c = lowered.count(d)
        if c:
            detail[d] = c * repeat
            delta -= c * repeat * 2

    return delta, detail


if st.button("🧮 코 수 계산하기", type="primary"):
    if not line_text.strip():
        st.warning("도안 문장을 입력해주세요.")
    else:
        delta, detail = count_st_changes(line_text)
        result = start_sts + delta

        st.subheader("📌 계산 결과")

        st.write(f"- 시작 코 수: **{start_sts}코**")
        st.write(f"- 변화량: **{delta:+}코**")
        st.write(f"- 👉 최종 코 수: **{result}코**")

        with st.expander("🔍 상세 계산 보기"):
            for k, v in detail.items():
                sign = "+" if k in INC_PATTERNS else "-"
                st.write(f"• {k} × {v} → {sign}{v}")


# ============================================================
# 3️⃣ ChatGPT에게 물어볼 때 쓸 프롬프트 만들기 (최종 정제 버전)
# ============================================================

st.header("3️⃣ ChatGPT 프롬프트 생성기")

st.markdown("""
✔ **프롬프트에는 두 가지 정보만 포함됩니다.**  
1) 시작 코 수  
2) 도안 한 줄  

이 외의 계산 결과/예상코수/참고 문구 등은 **일절 포함되지 않습니다.**
""")

colA, colB = st.columns(2)

with colA:
    prompt_sts = st.number_input(
        "🔢 (프롬프트용) 시작 코 수",
        min_value=0,
        value=start_sts,
        step=1,
    )

prompt_line = st.text_area(
    "✏️ (프롬프트용) 도안 한 줄",
    value=line_text,
    height=120,
    placeholder="ChatGPT에게 분석시킬 도안 한 줄을 붙여넣으세요."
)

if st.button("📝 프롬프트 생성하기", type="primary"):
    if not prompt_line.strip():
        st.warning("도안 한 줄을 입력해주세요.")
    else:
        final_prompt = f"""
너는 뜨개질 서술형 도안의 코 수 변화를 분석하는 전문가야.

아래 정보를 기반으로 해당 줄의 코 수 증가/감소량과 최종 코 수를 계산해 줘:

- 시작 코 수: {prompt_sts}코
- 도안 한 줄: "{prompt_line.strip()}"

위 내용을 분석해서:
1) 증가/감소한 코 수  
2) 최종 코 수  
3) 계산 과정 설명  
을 한국어로 설명해 줘.
""".strip()

        st.subheader("📋 ChatGPT에 붙여넣을 프롬프트")

        st.text_area("아래 내용을 복사하면 됩니다:", value=final_prompt, height=260)
        st.success("프롬프트가 생성되었습니다! ChatGPT 창에 붙여넣어 사용하세요.")