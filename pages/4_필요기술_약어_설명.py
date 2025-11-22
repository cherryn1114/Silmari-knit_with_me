import streamlit as st
from openai import OpenAI
import json
import os
from PIL import Image
import numpy as np

client = OpenAI()

IMG_DIR = "assets/chart_from_excel"
MANIFEST = "assets/chart_from_excel/manifest.json"

st.title("🔧 필요 기술 / 약어 설명")

uploaded_file = st.file_uploader("이미지 또는 PDF 업로드", type=["png", "jpg", "jpeg"])

use_ai = st.checkbox("🤖 GPT 기반 의미 분석 사용 (추천)", value=True)

# -----------------------------
# 유틸 함수
# -----------------------------
def load_manifest():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)

def encode_image(image: Image.Image):
    arr = np.array(image.resize((256, 256))).astype(np.uint8)
    return arr.tolist()

def llm_match(img: Image.Image, manifest):
    prompt = """
너는 뜨개질 차트 기호 전문가야.
아래 base64 이미지와 가장 유사한 기호를 찾고,
해당 기호의 이름과 설명을 JSON 형식으로 반환해줘.

반드시 JSON 한 줄로만 응답해.
{"abbr": "...", "desc": "...", "file": "..."}
"""

    buffered = encode_image(img)

    # ✨ 한글 포함을 위해 utf-8 인코딩 명시 + 문자열을 bytes로 변환하지 않음
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps({"img": buffered}, ensure_ascii=False)}
        ]
    )

    return response.output_text

# -----------------------------
# 실행
# -----------------------------
if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="업로드된 이미지", use_column_width=True)

    manifest = load_manifest()

    if use_ai:
        st.info("🤖 **GPT 기반 의미 분석 중...**")
        try:
            result = llm_match(image, manifest)
            st.success("✔ 결과:")
            st.write(result)

        except Exception as e:
            st.error(str(e))

    else:
        st.warning("📌 GPT 분석 비활성화됨. CLIP 기반 매칭만 진행됩니다.")
else:
    st.info("이미지를 업로드하면 분석이 시작됩니다.")