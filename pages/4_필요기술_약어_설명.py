import streamlit as st
from openai import OpenAI
import json
from PIL import Image
import numpy as np
import os

st.set_page_config(page_title="필요 기술 / 약어 설명", layout="wide")

client = OpenAI()

# 매니페스트 로드
MANIFEST_PATH = "assets/chart_from_excel/manifest.json"
with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    manifest = json.load(f)

# 모든 기호 이미지 로드
catalog = []
for sheet, item in manifest.items():
    if not isinstance(item, dict) or "items" not in item:
        continue
    for ch in item["items"]:
        catalog.append({
            "file": ch["file"],
            "abbr": ch.get("abbr", ""),
            "desc": ch.get("desc", ""),
            "sheet": sheet,
            "path": os.path.join("assets/chart_from_excel", ch["file"])
        })

st.title("📘 필요 기술 / 약어 설명")
st.markdown("이미지로 기호를 업로드하면 AI가 의미를 분석하고 가장 비슷한 기호를 추천해줍니다.")

uploaded = st.file_uploader("➡ 기호 이미지 업로드", type=["png", "jpg", "jpeg"])

if uploaded:
    img = Image.open(uploaded)
    st.image(img, caption="업로드한 이미지", use_column_width=True)

    # 🔥 Vision 모델로 의미 분석
    response = client.responses.create(
        model="gpt-4o-mini-tts",  # Vision 기능 있는 모델이면 변경 가능
        input=[
            {
                "role": "user",
                "content": [
                    "다음 이미지는 뜨개질 도안의 기호입니다. 이 기호가 나타내는 뜻을 한국어로 정확히 설명해줘.",
                    {"image": img}
                ]
            }
        ]
    )

    result_text = response.output_text
    st.subheader("🧠 AI 해석")
    st.write(result_text)

    # 🔍 카탈로그에서 가장 관련 높은 후보 출력 (LLM 활용)
    catalog_text = "\n".join([f"{c['abbr']} - {c['desc']}" for c in catalog])

    match = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
사용자가 업로드한 기호 의미:
{result_text}

아래는 가능한 기호 목록입니다:
{catalog_text}

가장 의미가 비슷한 5개를 정확도 높은 순서로 JSON 배열로 반환하세요.
형식:
[
  {{"abbr": "", "desc": "", "file": ""}}
]
"""
    )

    st.subheader("🔍 추천된 유사 기호")
    st.write(match.output_text)