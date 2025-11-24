# pages/5_서술형_도안_및_코수_추적.py

import re
from typing import Optional, Tuple, Any

import streamlit as st

from lib.pdf_utils import extract_pdf_text
from lib.upload_utils import uploader_with_history


st.set_page_config(
    page_title="✏️ 서술형 도안 & 코 수 추적",
    page_icon="✏️",
    layout="wide",
)

st.title("✏️ 서술형 도안 & 코 수 추적")

st.markdown(
    """
이 페이지에서는 **서술형 도안(PDF)** 을 올려서 텍스트를 추출하고,  
그 도안의 한 줄을 골라 코 수 변화를 계산해 볼 수 있어요.

1. 먼저 PDF를 업로드하고 텍스트를 추출해서 복사합니다.  
2. 그런 다음, 특정 줄(예: `k55, m1L`)과 시작 코 수를 넣어 **최종 코 수**를 계산해 보세요.
"""
)

st.divider()

# -------------------------------------------------------------------
# 1️⃣ PDF에서 텍스트 추출하기
# -------------------------------------------------------------------
st.header("1️⃣ 서술형 도안 PDF에서 텍스트 추출하기")

col_left, col_right = st.columns([1, 1.4])

with col_left:
    st.markdown("#### 📂 도안 PDF 업로드 / 선택")

    # uploader_with_history 가 **(UploadedFile, 저장경로)** 또는 None 을 반환한다고 가정
    uploaded_info: Optional[Tuple[Any, str]] = uploader_with_history(
        label="서술형 도안 PDF 업로드",
        key="text_pattern_pdf",
        # accept_types 나 기타 인자는 upload_utils 구현에 따라 무시될 수 있음
    )

    current_file_path: Optional[str] = None
    current_file_name: Optional[str] = None

    if uploaded_info:
        file_obj, saved_path = uploaded_info
        current_file_path = saved_path
        # Streamlit UploadedFile 이면 name 속성이 있음
        current_file_name = getattr(file_obj, "name", None) or saved_path

        st.success(f"PDF 파일이 업로드되었습니다.\n\n현재 사용 중인 파일: `{current_file_name}`")
    else:
        st.info("왼쪽 상단의 업로드 박스에서 서술형 도안 PDF를 올려 주세요.")

with col_right:
    st.markdown("#### 📄 PDF에서 텍스트 추출")

    if "pdf_extracted_text" not in st.session_state:
        st.session_state["pdf_extracted_text"] = ""

    if current_file_path:
        if st.button("📕 PDF에서 텍스트 추출하기", type="primary"):
            try:
                # 🔑 여기에서 **문자열 경로만** extract_pdf_text 에 넘김
                text = extract_pdf_text(current_file_path)
                st.session_state["pdf_extracted_text"] = text
                st.success("PDF에서 텍스트를 성공적으로 추출했습니다. 아래 텍스트 박스에서 복사해서 사용하세요.")
            except Exception as e:
                st.error(f"PDF 텍스트 추출 중 오류가 발생했습니다: {e}")
    else:
        st.button("📕 PDF에서 텍스트 추출하기", disabled=True)

    st.markdown("##### 🔎 추출된 도안 텍스트 (복사해서 사용하세요)")
    st.text_area(
        "추출된 도안 텍스트",
        key="pdf_extracted_text",
        height=250,
    )

st.divider()

# -------------------------------------------------------------------
# 2️⃣ 서술형 도안 한 줄에서 코 수 계산하기
# -------------------------------------------------------------------
st.header("2️⃣ 서술형 도안 한 줄에서 코 수 계산하기")

st.markdown(
    """
아래에 **현재 코 수**와 **해당 줄의 서술형 도안**을 적으면  
그 줄이 끝났을 때의 **최종 코 수**를 대략 계산해 줍니다.

예시)

* 시작 코 수: `56`  
* 서술형 도안: `k55, m1L` → 결과: **57코**

> ⚠️ 이 계산기는 **대략적인 참고용**이에요.  
> 도안에 따라 예외적인 기호/표현이 있을 수 있으니, 항상 도안 설명도 함께 확인해 주세요.
"""
)

calc_col1, calc_col2 = st.columns([1, 1])

with calc_col1:
    start_sts = st.number_input("현재(시작) 코 수", min_value=0, value=0, step=1)
    row_text = st.text_input(
        "서술형 도안 한 줄 (예: `k55, m1L` 또는 `k3, yo, k2tog`)",
        value="",
        help="해당 줄의 내용만 간단히 적어 주세요. 쉼표(,) 또는 공백으로 구분해도 됩니다.",
    )

    run_calc = st.button("🧮 이 줄의 코 수 계산하기", type="primary")

with calc_col2:
    st.subheader("결과")

    def estimate_delta(token: str) -> tuple[int, str]:
        """
        토큰 하나가 코 수에 얼마나 영향을 주는지 대략 추정.
        (규칙은 단순화된 버전이라 100% 정확하지는 않을 수 있음)
        """
        t = token.strip().lower()
        if not t:
            return 0, "공백"

        # 숫자만 있는 경우 (코 수 변화 없음)
        if t.isdigit():
            return 0, "숫자"

        # k55 / p12 같은 것: 코 수는 유지
        m = re.match(r"(k|p)(\d+)", t)
        if m:
            n = int(m.group(2))
            return 0, f"{m.group(1)}{n} (코 수 변화 없음)"

        # yo (구멍 만들기) → +1 (또는 숫자가 붙으면 그 수만큼)
        if "yo" in t:
            m = re.search(r"(\d+)", t)
            inc = int(m.group(1)) if m else 1
            return inc, f"yo 계열 늘리기 (+{inc})"

        # m1 / m1l / m1r 등 → +1
        if t.startswith("m1"):
            return 1, "M1 계열 늘리기 (+1)"

        # kfb / pfb / inc 계열 → +1 로 처리
        if t in {"kfb", "pfb"} or "inc" in t:
            return 1, "늘리기(+1)"

        # tog / ssk / ssp / k2tog / p3tog 등 → 모아뜨기
        if "tog" in t or t.startswith("ssk") or t.startswith("ssp"):
            m = re.search(r"(\d+)", t)
            if m:
                n = int(m.group(1))
                # n코를 1코로 모으는 것으로 가정 → -(n-1)
                dec = n - 1
                return -dec, f"{n}코 모아뜨기 (–{dec})"
            # 숫자가 없으면 2코 모아뜨기로 가정 → -1
            return -1, "2코 모아뜨기 (–1)"

        # 그 외 기호는 기본적으로 코 수 변화 없다고 가정
        return 0, "코 수 변화 없음"

    if run_calc and row_text:
        tokens = re.split(r"[,\s]+", row_text.strip())
        cur = int(start_sts)
        breakdown = []

        for tok in tokens:
            if not tok:
                continue
            delta, reason = estimate_delta(tok)
            prev = cur
            cur += delta
            breakdown.append((tok, prev, delta, cur, reason))

        st.markdown(f"### ✅ 계산 결과: **{start_sts}코 → {cur}코**")

        st.markdown("#### 🔍 토큰별 변화 내역")
        for tok, prev, delta, after, reason in breakdown:
            sign = "+" if delta > 0 else ""
            st.write(f"- `{tok}` : {prev}코 → {after}코 ({sign}{delta}), _{reason}_")

    elif run_calc and not row_text:
        st.warning("먼저 서술형 도안 한 줄을 입력해 주세요.")


st.divider()

st.markdown(
    """
### 📎 홈으로 돌아가기

- [🏠 HOME 페이지](HOME.py)를 통해 다른 기능(뜨개 약어 사전, 차트 기호 사전 등)으로 이동할 수 있어요.
"""
)