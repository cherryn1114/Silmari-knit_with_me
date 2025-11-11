# pages/4_필요기술_약어_설명.py
import streamlit as st
from lib import parser, pdf_utils

st.set_page_config(page_title="실마리 — 필요 기술/약어", page_icon="🧰", layout="centered")
st.title("🧰 도안에 사용된 필요 기술 / 약어 설명")

if "uploaded_bytes" not in st.session_state:
    st.error("홈에서 먼저 도안을 업로드하세요.")
    st.page_link("app.py", label="⬅ 홈으로")
    st.stop()

lib = parser.load_lib("lib/symbols.json")
pdf_bytes = st.session_state["uploaded_bytes"]
name = st.session_state.get("uploaded_name", "uploaded.pdf")

st.write(f"업로드된 파일: **{name}**")

# (선택) PDF 텍스트에서 약어 자동 추정 (간단 키워드 매칭)
auto = st.toggle("PDF 텍스트에서 약어 자동 추정 시도", value=True)
detected = set()
if auto and name.lower().endswith(".pdf"):
    try:
        texts = pdf_utils.extract_text_per_page(pdf_bytes)
        raw = "\n".join(texts).lower()
        for key, item in lib.items():
            keys = set([key.lower()] + [a.lower() for a in item.get("aliases", [])])
            if any(k in raw for k in keys):
                detected.add(key)
    except Exception as e:
        st.warning(f"자동 추정 중 오류: {e}")

st.write("아래에서 이 도안에 쓰인 기술/약어를 확인/수정하세요.")
selected = st.multiselect(
    "도안에 사용된 기법 선택(자동 추정 결과 포함)",
    options=list(lib.keys()),
    default=sorted(detected)
)

st.subheader("설명/링크 모음")
if not selected:
    st.info("선택된 항목이 없습니다.")
else:
    for k in selected:
        item = lib[k]
        st.markdown(f"### {k} — {item['name_ko']}")
        st.write(item["desc_ko"])
        if item.get("compare"):
            st.caption("비교 기법: " + ", ".join(item["compare"]))
        if item.get("media"):
            st.write("관련 미디어:")
            for m in item["media"]:
                st.write(f"- {m['type']}: {m['url']}")

st.divider()
st.page_link("app.py", label="⬅ 홈으로")
st.page_link("pages/5_서술형_설명.py", label="➡ 페이지 5 (서술형 설명)")