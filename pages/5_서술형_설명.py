# pages/5_서술형_설명.py
import streamlit as st
from lib import parser

st.set_page_config(page_title="실마리 — 서술형 설명", page_icon="📝", layout="centered")
st.title("📝 서술형 도안 설명")

if "uploaded_bytes" not in st.session_state:
    st.error("홈에서 먼저 도안을 업로드하세요.")
    st.page_link("app.py", label="⬅ 홈으로")
    st.stop()

lib = parser.load_lib("lib/symbols.json")

st.write("도안의 각 ‘행’ 또는 ‘세트’를 서술형으로 입력하면 전개/코수 변화를 만들어 드려요.")
st.caption("예: `[(p, k) x 6, m1L] x 8`  또는  `*k, p* 4회; yo; ssk`")

pattern = st.text_area("서술형 입력", "[(p, k) x 6, m1L] x 8", height=120)
start_sts = st.number_input("이 구간 시작 코 수", min_value=0, max_value=10000, value=64)

if st.button("전개 및 설명 생성"):
    tokens = parser.expand_sequence(pattern)
    st.write(f"**전개 스텝 수:** {len(tokens)}")
    with st.expander("풀 전개 보기"):
        st.code(", ".join(tokens))
    rows = parser.compute_counts(tokens, start_sts, lib)
    st.write("### 코수 변화 로그")
    st.dataframe(
        [{"스텝": s, "토큰": t, "Δ코수": d, "기대 코수": c} for (s, t, c, d) in rows],
        use_container_width=True
    )
    expected_end = rows[-1][2] if rows else start_sts
    st.success(f"이 구간 종료 후 기대 코수: **{expected_end}코**")

st.divider()
st.page_link("app.py", label="⬅ 홈으로")
st.page_link("pages/6_코수_추적_체크.py", label="➡ 페이지 6 (코수 추적/체크)")