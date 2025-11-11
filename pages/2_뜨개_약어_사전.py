# pages/2_뜨개_약어_사전.py
import streamlit as st
import json
from pathlib import Path
from lib import parser

st.set_page_config(page_title="실마리 — 약어 사전", page_icon="📚", layout="centered")
st.title("📚 뜨개 약어 사전")

lib = parser.load_lib("lib/symbols.json")

q = st.text_input("약어/용어를 검색하세요 (예: m1l, ssk, 오른모아, 걸어코)", "")
if q:
    key, item = parser.find_term(q)
    if key:
        st.success(f"**{item['name_ko']}**  (키: `{key}`)")
        st.write(item["desc_ko"])
        if item.get("compare"):
            st.info("비교 기법: " + ", ".join(item["compare"]))
    else:
        st.error("관련 용어를 찾지 못했어요. 철자를 확인하거나 다른 표현을 시도해보세요.")

st.divider()
st.page_link("app.py", label="⬅ 홈으로")
st.page_link("pages/3_차트_기호_사전.py", label="➡ 페이지 3 (차트 기호 사전)")