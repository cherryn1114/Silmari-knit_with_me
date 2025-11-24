# pages/5_서술형_도안_및_코수_추적.py

import re
from collections import Counter

import streamlit as st

from lib.pdf_utils import extract_pdf_text
from lib.upload_utils import uploader_with_history


st.set_page_config(
    page_title="서술형 도안 & 코수 추적",
    page_icon="📘",
    layout="wide",
)

st.title("📘 서술형 도안 & 코수 추적")


# ----------------------------------------------------
# 0. 공통 도움말
# ----------------------------------------------------
st.markdown(
    """
이 페이지에서는 **서술형(문장형) 도안**을 다룰 수 있어요.

1. **PDF 도안에서 텍스트 추출** → 복사해서 사용  
2. **한 줄 도안에서 코 수 변화 계산** → 시작 코 수 + (늘림/줄임) = 최종 코 수

**주의:**  
- k, p 처럼 단순 겉뜨기/안뜨기는 코 수 변화가 없다고 가정해요.  
- `yo, m1l, m1r …` 는 **늘리는 기호(+1)**,  
  `k2tog, ssk, ssp, p2tog …` 는 **모아뜨기(–1)** 로 계산해요.  
- `… 3회 반복`, `… 3번 반복`, `… 3 times`, `… x3` 처럼  
  **반복 횟수**가 적힌 문장은 한 번 계산한 뒤 그 횟수만큼 곱해요.
"""
)

st.divider()

# ====================================================
# 1️⃣ PDF에서 도안 텍스트 추출하기
# ====================================================
st.header("1️⃣ PDF에서 도안 텍스트 추출하기")

col_u1, col_u2 = st.columns([1.4, 2])

with col_u1:
    st.markdown("#### 📂 서술형 도안 PDF 업로드")

    uploaded_file, current_path = uploader_with_history(
        key="pattern_pdf",
        label="Drag and drop file here",
        help="서술형 도안이 들어 있는 PDF 파일을 올려 주세요.",
        type=["pdf"],
    )

    if current_path:
        st.success(f"PDF 파일이 업로드되었습니다.\n\n현재 사용 중인 파일: `{current_path}`")
    else:
        st.info("왼쪽에 있는 업로드 박스에 PDF 파일을 올려 주세요.")

    if current_path:
        if st.button("📄 PDF에서 텍스트 추출하기", type="primary"):
            try:
                text = extract_pdf_text(current_path)
                if not text.strip():
                    st.warning("PDF에서 읽어 온 텍스트가 비어 있습니다. 스캔본(이미지) PDF일 수도 있어요.")
                st.session_state["extracted_pattern_text"] = text
                st.success("PDF에서 텍스트를 추출했습니다. 아래 텍스트 박스를 확인해 주세요.")
            except Exception as e:
                st.error(f"PDF 텍스트 추출 중 오류가 발생했습니다: {e}")

with col_u2:
    st.markdown("#### 📋 추출된 도안 텍스트 (복사해서 사용하세요)")
    extracted = st.session_state.get("extracted_pattern_text", "")
    st.text_area(
        "PDF에서 읽어 온 텍스트",
        value=extracted,
        height=260,
    )

st.divider()

# ====================================================
# 2️⃣ 서술형 도안 한 줄에서 코 수 계산하기
# ====================================================
st.header("2️⃣ 서술형 도안 한 줄에서 코 수 계산하기")

st.markdown(
    """
예시:

- `k55, m1L`  →  **늘림 1코** → 시작 56코라면 **최종 57코**  
- `k1, m1R 총 3회 반복`  →  (한 번에 +1코) × 3회 = **+3코 증가**  
- `repeat k5, ssk 7 times`  →  ssk 한 번당 –1코 줄어듦 → **–7코 감소**

아래 입력 칸에는 **한 줄(또는 한 구간)의 도안 설명만** 넣어 주세요.
"""
)

col1, col2 = st.columns([1, 2])

with col1:
    start_sts = st.number_input("현재(시작) 코 수", min_value=0, step=1, value=0)

with col2:
    line_text = st.text_area(
        "도안 한 줄(또는 한 구간) 설명",
        placeholder="예) k55, m1L  \n예) k1, m1R 총 3회 반복  \n예) repeat k5, ssk 7 times",
        height=120,
    )


# ----------------------------------------------------
# 증·감 기호 정의
# ----------------------------------------------------
# 모두 소문자로 처리해서 비교할 예정
INCREASE_WORDS = [
    "yo",
    "m1",
    "m1l",
    "m1r",
    "m1lp",
    "m1rp",
    "inc",
    "kfb",
    "pfb",
    "kll",
    "krl",
]

DECREASE_WORDS = [
    "k2tog",
    "k3tog",
    "ssk",
    "ssp",
    "skpo",
    "skp",
    "sk2p",
    "p2tog",
    "p3tog",
    "cdd",
]


def _normalize_text(text: str) -> str:
    """공백/구두점 정리 + 소문자 변환."""
    t = text.replace("\n", " ")
    # 괄호, 콤마 등은 구분을 위해 공백으로
    for ch in [",", ";", ":", "(", ")", "[", "]"]:
        t = t.replace(ch, " ")
    return t.lower()


def _extract_repeat_info(text: str) -> tuple[str, int]:
    """
    문장 끝의 '3회', '3번', '3 times', 'x3' 등을 찾아서 (본문, 반복횟수) 반환.
    찾지 못하면 (원본문, 1)
    """
    t = text.strip()
    tl = t.lower()

    # 패턴 1: "... 3회 반복", "... 3 times", "... 3번"
    m = re.search(r"(.*?)(\d+)\s*(회|번|times?)\s*(반복)?\s*$", tl)
    if m:
        count = int(m.group(2))
        base = t[: m.start(2)].strip(" ,.;:()")
        return base, max(count, 1)

    # 패턴 2: "... x3" / "... ×3" / "... * 3"
    m2 = re.search(r"(.*?)[x×*]\s*(\d+)\s*$", tl)
    if m2:
        count = int(m2.group(2))
        base = t[: m2.start(2)].strip(" ,.;:()x×*")
        return base, max(count, 1)

    return t, 1


def _count_words(words, text_lower: str) -> Counter:
    """
    INCREASE_WORDS / DECREASE_WORDS 리스트에 있는 단어들이
    text_lower 안에 각각 몇 번 등장하는지 센다.
    """
    cnt = Counter()
    for w in words:
        pattern = r"\b" + re.escape(w) + r"\b"
        found = re.findall(pattern, text_lower)
        if found:
            cnt[w] = len(found)
    return cnt


def compute_delta(text: str) -> tuple[int, Counter, Counter, int]:
    """
    한 번(1회) 수행했을 때의 증·감 코 수를 계산하고,
    반복 횟수를 반영한 총 변화량도 함께 반환.

    반환:
        total_delta  : 총 코 수 변화량 (늘림 - 줄임)
        inc_counts   : 늘림 기호별 등장 횟수 (1회 기준)
        dec_counts   : 줄임 기호별 등장 횟수 (1회 기준)
        repeat_count : 반복 횟수
    """
    if not text.strip():
        return 0, Counter(), Counter(), 1

    # 반복 정보 분리
    base_text, repeat_count = _extract_repeat_info(text)
    base_norm = _normalize_text(base_text)

    inc_counts = _count_words(INCREASE_WORDS, base_norm)
    dec_counts = _count_words(DECREASE_WORDS, base_norm)

    inc_total = sum(inc_counts.values())
    dec_total = sum(dec_counts.values())

    unit_delta = inc_total - dec_total          # 1회 수행 시 변화량
    total_delta = unit_delta * repeat_count     # 반복까지 반영한 변화량

    return total_delta, inc_counts, dec_counts, repeat_count


# ----------------------------------------------------
# 계산 버튼 동작
# ----------------------------------------------------
if st.button("✅ 이 줄 코 수 계산하기", type="primary"):
    if not line_text.strip():
        st.warning("도안 설명 한 줄을 입력해 주세요.")
    else:
        delta, inc_counts, dec_counts, repeat_count = compute_delta(line_text)

        final_sts = start_sts + delta

        st.subheader("🔎 계산 결과")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"- **시작 코 수:** {start_sts}코")
            st.markdown(f"- **반복 횟수:** × {repeat_count}")

            inc_total = sum(inc_counts.values()) * repeat_count
            dec_total = sum(dec_counts.values()) * repeat_count

            st.markdown(f"- **늘림 총합:** +{inc_total}코")
            st.markdown(f"- **줄임 총합:** −{dec_total}코")

            if delta == 0:
                st.info(f"코 수 변화가 없는 줄로 계산되었습니다. → **최종도 {final_sts}코**")
            elif delta > 0:
                st.success(f"총 **+{delta}코** 늘어납니다. → **최종 {final_sts}코**")
            else:
                st.error(f"총 **{delta}코**(줄어듦) 변화입니다. → **최종 {final_sts}코**")

        with col_b:
            st.markdown("#### 🔹 늘림 기호별 개수 (1회 기준)")
            if inc_counts:
                for k, v in inc_counts.items():
                    st.markdown(f"- `{k}` : {v}회 → +{v}코")
            else:
                st.write("늘림 기호가 발견되지 않았어요.")

            st.markdown("#### 🔻 줄임 기호별 개수 (1회 기준)")
            if dec_counts:
                for k, v in dec_counts.items():
                    st.markdown(f"- `{k}` : {v}회 → −{v}코")
            else:
                st.write("줄임 기호가 발견되지 않았어요.")

        st.info(
            "다음 줄(다음 단계)을 계산할 때는 **위에서 나온 최종 코 수를 "
            "다음 줄의 시작 코 수로 넣어서** 계속 이어서 계산하면 됩니다."
        )

st.divider()

st.markdown("🏠 [HOME 로 돌아가기](HOME.py)")