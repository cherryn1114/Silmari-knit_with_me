# pages/3_차트_기호_사전.py
import streamlit as st
from lib import parser

st.set_page_config(page_title="실마리 — 차트 기호 사전", page_icon="🗂️", layout="centered")
st.title("🗂️ 차트 도안 기호 사전")

lib = parser.load_lib("lib/symbols.json")

st.write("자주 쓰는 기호/약어 목록입니다. (각 항목을 클릭해 설명 보기)")
for k, v in lib.items():
    with st.expander(f"{k} — {v['name_ko']}"):
        st.write(v["desc_ko"])
        if v.get("compare"):
            st.info("비교 기법: " + ", ".join(v["compare"]))
        if v.get("media"):
            st.write("관련 미디어:")
            for m in v["media"]:
                st.write(f"- {m['type']}: {m['url']}")

st.divider()
st.page_link("app.py", label="⬅ 홈으로")