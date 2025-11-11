# pages/6_코수_추적_체크.py
import streamlit as st
from lib import parser

st.set_page_config(page_title="실마리 — 코수 추적/체크", page_icon="✅", layout="centered")
st.title("✅ 코수 추적 / 체크")

if "uploaded_bytes" not in st.session_state:
    st.error("홈에서 먼저 도안을 업로드하세요.")
    st.page_link("app.py", label="⬅ 홈으로")
    st.stop()

lib = parser.load_lib("lib/symbols.json")

st.write("행 단위로 서술형을 입력하고, 각 행 완료 시 현재 코 수를 체크해 보세요.")
st.caption("멀티라인 예시:\nR1: [(p, k) x 6, m1L] x 2\nR2: k2tog, k, yo, p2tog, m1R")

text = st.text_area("행별 서술형 입력 (한 줄 = 한 행)", "R1: [(p, k) x 6, m1L] x 2\nR2: k2tog, k, yo, p2tog, m1R", height=160)
start = st.number_input("시작 코 수", min_value=0, max_value=10000, value=64)

if st.button("행별 기대 코수 계산"):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cur = start
    report = []
    for ln in lines:
        # "R1: ..." 형식 지원
        if ":" in ln:
            label, patt = ln.split(":", 1)
            label = label.strip()
        else:
            label, patt = "Row", ln
        tokens = parser.expand_sequence(patt.strip())
        rows = parser.compute_counts(tokens, cur, lib)
        end_count = rows[-1][2] if rows else cur
        delta = end_count - cur
        report.append((label, patt.strip(), cur, end_count, delta))
        cur = end_count

    st.write("### 행별 기대 코수")
    st.dataframe(
        [{"행": r[0], "서술": r[1], "행 시작 코수": r[2], "행 종료 기대 코수": r[3], "Δ(이 행)": r[4]} for r in report],
        use_container_width=True
    )

    st.info(f"모든 행 종료 후 기대 코수: **{cur}코**")

    st.subheader("내 실제 코수 체크")
    actual = st.number_input("지금 실제 코 수", min_value=0, max_value=10000, value=cur)
    if actual != cur:
        st.warning(f"불일치: 기대 {cur}코 vs 실제 {actual}코 (차이 {actual-cur}코)")
        st.caption("증가/감소가 있었던 행을 우선 확인해 보세요(yo/m1L/m1R/ssk/k2tog 등).")
    else:
        st.success("현재 코수가 기대치와 일치합니다.")

st.divider()
st.page_link("app.py", label="⬅ 홈으로")