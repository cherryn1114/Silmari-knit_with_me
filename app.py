import streamlit as st

st.set_page_config(page_title="실마리 - 뜨개 도우미", page_icon="🧶", layout="centered")

st.title("🧶 실마리 (Silmari)")
st.subheader("AI 뜨개 도우미 — 도안 업로드 후 원하는 기능을 선택하세요")

st.divider()
st.header("도안 업로드 (PDF / PNG / JPG)")
upl = st.file_uploader("파일을 업로드하세요", type=["pdf","png","jpg","jpeg"])
if upl is not None:
    st.session_state["uploaded_name"] = upl.name
    st.session_state["uploaded_bytes"] = upl.read()
    st.success(f"업로드 완료: {upl.name}")

st.divider()
st.markdown("### 이동할 페이지")
st.page_link("pages/2_뜨개_약어_사전.py", label="📘 뜨개 약어 사전")
st.page_link("pages/3_차트_기호_사전.py", label="📊 차트 기호 사전")
st.page_link("pages/4_필요기술_약어_설명.py", label="🧰 필요 기술/약어 설명 (업로드 필요)")
st.page_link("pages/5_서술형_설명.py", label="📝 서술형 도안 설명 (업로드 필요)")
st.page_link("pages/6_코수_추적_체크.py", label="✅ 코수 추적/체크 (업로드 필요)")
st.caption("© 2025 실마리 | MVP 데모")
