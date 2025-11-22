# pages/4_필요기술_약어_설명.py

import streamlit as st
from openai import OpenAI
import os
import json
import base64
from pathlib import Path
from collections import defaultdict

from PIL import Image
import numpy as np

from lib import parser  # symbols.json, symbols_extra.json 로딩용

# ---------- 설정 ----------
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
IMG_ROOT = ASSETS_DIR / "chart_from_excel"
MANIFEST_PATH = IMG_ROOT / "manifest.json"

# OpenAI 클라이언트 (환경변수 OPENAI_API_KEY 필요)
# 없으면 나중에 체크해서 안내만 하고, 앱은 계속 동작하게 함.
client = None
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    client = OpenAI()

st.set_page_config(
    page_title="필요 기술 / 약어 설명",
    page_icon="📘",
    layout="wide",
)

st.title("📘 필요 기술 / 약어 설명")


# -----------------------------------------------------------------------------
# 0. 데이터 로딩 (symbols 사전 + 차트 기호 manifest)
# -----------------------------------------------------------------------------
@st.cache_resource
def load_symbol_lib():
    base = parser.load_lib("symbols.json")
    try:
        extra = parser.load_lib("symbols_extra.json")
    except Exception:
        extra = {}
    merged = {**base, **extra}
    return merged


@st.cache_resource
def load_chart_manifest():
    if not MANIFEST_PATH.exists():
        return {}

    with MANIFEST_PATH.open(encoding="utf-8") as f:
        manifest = json.load(f)

    # 평탄화된 아이콘 리스트 준비
    icons = []
    for sheet_title, sheet in manifest.items():
        img_dir = Path(sheet.get("img_dir", ""))  # 예: assets/chart_from_excel/1코_기호
        for it in sheet.get("items", []):
            file_name = it.get("file")
            abbr = it.get("abbr") or ""
            desc = it.get("desc") or ""
            full_path = img_dir / file_name
            icons.append(
                {
                    "sheet": sheet_title,
                    "file": file_name,
                    "path": full_path,
                    "abbr": abbr,
                    "desc": desc,
                }
            )
    return manifest, icons


symbol_lib = load_symbol_lib()
manifest, chart_icons = load_chart_manifest()


# -----------------------------------------------------------------------------
# 1. 텍스트 기반 필요 기술 / 약어 인식
# -----------------------------------------------------------------------------
st.header("1️⃣ 텍스트로 필요한 기술 / 약어 정리")

st.write(
    "도안 설명이나 필요한 기술 목록을 아래에 붙여 넣으면, "
    "뜨개 약어 사전과 비교해서 **알려진 약어/용어**를 찾아 정리해 줍니다."
)

input_text = st.text_area(
    "도안 설명이나 필요한 기술/약어를 붙여넣으세요.",
    height=180,
    placeholder="예) k2tog, ssk, YO, 중심 5코 모아뜨기, 오른코 겹쳐 3코 모아뜨기 …",
)

# 심플 매칭: key / name_ko / name_en / aliases 에 입력 텍스트가 포함되는지
def find_abbr_hits(text: str):
    text_low = text.lower()
    hits = []
    if not text_low.strip():
        return hits

    for key, v in symbol_lib.items():
        names = [key, v.get("name_en", ""), v.get("name_ko", "")]
        names += v.get("aliases", [])

        found = False
        for name in names:
            n = (name or "").strip()
            if not n:
                continue
            if n.lower() in text_low:
                found = True
                break
        if found:
            hits.append(
                {
                    "key": key,
                    "name_en": v.get("name_en", ""),
                    "name_ko": v.get("name_ko", ""),
                    "desc": v.get("desc_ko", ""),
                }
            )
    return hits


abbr_hits = find_abbr_hits(input_text)

st.subheader(f"🔍 인식된 기술/약어: {len(abbr_hits)}개")

if abbr_hits:
    for h in abbr_hits:
        title = h["key"]
        ko = h["name_ko"]
        en = h["name_en"]
        st.markdown(f"**{title}** — {en} / {ko}")
        if h["desc"]:
            st.caption(h["desc"])
        st.markdown("---")
else:
    st.info("텍스트에서 인식된 약어/차트 기호가 아직 없습니다. 위에 내용을 붙여 넣어 보세요.")


# -----------------------------------------------------------------------------
# 2. 차트 기호 이미지로 비슷한 기호 찾기 (이미지 매칭)
# -----------------------------------------------------------------------------
st.header("2️⃣ 차트 기호 이미지로 비슷한 기호 찾기")

st.write(
    "PDF 도안에서 **차트 기호 한 칸만 스크린샷** 해서 업로드하면, "
    "엑셀에서 가져온 162개의 차트 기호 중에서 **가장 비슷한 기호 후보**를 찾아 보여줍니다."
)

uploaded_chart_img = st.file_uploader(
    "차트 기호 스크린샷(이미지)을 업로드하세요. (PNG / JPG)", type=["png", "jpg", "jpeg"]
)

# ---- 아이콘 벡터 준비 (간단한 평균 풀링 특징) ----
@st.cache_resource
def build_icon_vectors(icons_list):
    db = []
    for icon in icons_list:
        path = BASE_DIR / icon["path"]
        if not path.exists():
            continue
        try:
            img = Image.open(path).convert("L").resize((64, 64))
            arr = np.asarray(img, dtype=np.float32) / 255.0
            vec = arr.flatten()
            vec = vec / (np.linalg.norm(vec) + 1e-8)
            icon_copy = dict(icon)
            icon_copy["vec"] = vec
            db.append(icon_copy)
        except Exception:
            continue
    return db


icon_db = build_icon_vectors(chart_icons)


def compute_vec_from_upload(uploaded_file):
    img = Image.open(uploaded_file).convert("L").resize((64, 64))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    vec = arr.flatten()
    vec = vec / (np.linalg.norm(vec) + 1e-8)
    return img, vec


def find_similar_icons(uploaded_file, topk=5):
    if not icon_db:
        return [], None

    up_img, up_vec = compute_vec_from_upload(uploaded_file)

    scores = []
    for icon in icon_db:
        vec = icon["vec"]
        sim = float(np.dot(up_vec, vec))  # 코사인 유사도
        scores.append((sim, icon))

    scores.sort(key=lambda x: x[0], reverse=True)
    best = scores[:topk]
    return best, up_img


if uploaded_chart_img is not None:
    st.image(uploaded_chart_img, caption="업로드한 기호 이미지", use_column_width=False, width=260)

    if st.button("🔎 비슷한 차트 기호 찾기"):
        matches, up_img = find_similar_icons(uploaded_chart_img, topk=5)
        if not matches:
            st.warning("차트 아이콘 인덱스를 찾지 못했습니다. (manifest.json 또는 PNG 경로를 확인해 주세요.)")
        else:
            st.success("가장 비슷한 차트 기호 후보들입니다.")
            cols = st.columns(len(matches))
            for col, (sim, icon) in zip(cols, matches):
                path = BASE_DIR / icon["path"]
                try:
                    col.image(str(path), use_column_width=True)
                except Exception:
                    col.write("(이미지 로드 실패)")

                label = icon.get("abbr") or "(이름 미입력)"
                desc = icon.get("desc") or ""
                col.markdown(f"**{label}**")
                col.caption(f"{icon['sheet']} · 유사도 {sim:.2f}")
                if desc:
                    col.write(desc)

            st.markdown("---")
else:
    st.info("차트 기호 스크린샷을 업로드하면 비슷한 기호를 찾아줍니다.")


# -----------------------------------------------------------------------------
# 3. GPT에게 이 기호 설명 요청 (앱 안에서)
# -----------------------------------------------------------------------------
st.header("3️⃣ GPT에게 이 기호 설명 요청하기 (선택 기능)")

if client is None:
    st.warning(
        "OpenAI API 키가 설정되어 있지 않아, 앱 안에서 GPT 호출은 사용할 수 없습니다.\n\n"
        "`OPENAI_API_KEY` 환경변수를 설정하거나, 아래 4️⃣ 프롬프트를 복사해서 ChatGPT에 직접 물어보세요."
    )
else:
    st.write(
        "업로드한 차트 기호 이미지와 위에서 인식된 약어/기술 이름을 함께 GPT에게 보내 "
        "**이 기호가 어떤 의미인지, 어떤 뜨개 기법인지 한글로 설명**해달라고 요청합니다."
    )

    # 이미지가 있어야 Vision 사용 가능
    can_call_gpt = uploaded_chart_img is not None and client is not None

    if not uploaded_chart_img:
        st.info("먼저 위 2️⃣에서 차트 기호 이미지를 업로드해 주세요.")
    elif client is None:
        pass
    else:
        if st.button("🧵 GPT에게 이 기호 설명 요청하기"):
            try:
                # 업로드 이미지 Base64 인코딩
                img_bytes = uploaded_chart_img.getvalue()
                b64_img = base64.b64encode(img_bytes).decode("utf-8")
                data_url = f"data:image/png;base64,{b64_img}"

                # 텍스트 컨텍스트 구성 (인식된 약어 / 후보명 등)
                context_lines = []

                if abbr_hits:
                    context_lines.append("텍스트에서 인식된 약어/기술 목록:")
                    for h in abbr_hits:
                        line = f"- {h['key']} / {h['name_en']} / {h['name_ko']}"
                        context_lines.append(line)

                # 이미지 매칭 후보를 다시 한 번 계산해서 GPT에 힌트로 제공
                matches, _ = (find_similar_icons(uploaded_chart_img, topk=5)
                              if uploaded_chart_img is not None else ([], None))
                if matches:
                    context_lines.append("")
                    context_lines.append("이미지로 매칭된 차트 기호 후보들:")
                    for sim, icon in matches:
                        label = icon.get("abbr") or "(이름 미입력)"
                        context_lines.append(f"- {label} (sheet: {icon['sheet']}, sim: {sim:.2f})")

                context_text = "\n".join(context_lines) if context_lines else "추가 힌트 없음."

                # OpenAI Responses API 호출 (Vision + 텍스트)
                resp = client.responses.create(
                    model="gpt-4.1-mini",  # 필요에 따라 gpt-4.1, gpt-4.1-mini 등으로 변경 가능
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_image",
                                    "image_url": data_url,
                                },
                                {
                                    "type": "input_text",
                                    "text": (
                                        "이 이미지는 뜨개질 도안의 차트 기호 한 칸입니다. "
                                        "이미지와 아래 힌트를 참고하여, 이 기호가 어떤 의미의 차트 기호인지, "
                                        "어떤 뜨개 기법을 의미하는지 **한국어로 자세히** 설명해 주세요.\n\n"
                                        f"{context_text}"
                                    ),
                                },
                            ],
                        }
                    ],
                )

                # 응답 텍스트 추출
                try:
                    # 새 SDK의 responses.create 결과 구조에 맞게 처리
                    out = []
                    for item in resp.output:
                        for c in item.content:
                            if getattr(c, "type", "") == "output_text":
                                out.append(c.text)
                    answer = "\n\n".join(out) if out else str(resp)
                except Exception:
                    # 혹시 구조가 다르면 전체 객체를 문자열로 출력
                    answer = str(resp)

                st.success("GPT 응답입니다.")
                st.write(answer)

            except Exception as e:
                st.error(f"GPT 호출 중 오류: {e}")


# -----------------------------------------------------------------------------
# 4. ChatGPT에 직접 물어볼 때 쓸 프롬프트 생성
# -----------------------------------------------------------------------------
st.header("4️⃣ ChatGPT에 직접 물어볼 때 쓸 프롬프트")

st.write(
    "만약 이 앱에서 GPT 호출이 잘 안 되거나, "
    "직접 ChatGPT 웹사이트/앱에 물어보고 싶다면 아래 프롬프트를 복사해서 사용하세요."
)

# 프롬프트에 들어갈 요약 정보 구성
prompt_lines = [
    "너는 뜨개질 차트 기호를 분석하는 전문가야.",
    "내가 곧 첨부할 이미지는 뜨개 도안(차트)에서 잘라낸 ‘기호 한 칸’이야.",
    "",
    "이미지의 모양을 보고 아래 형식으로 한국어로 답해 줘.",
    "",
    "1. 이 기호가 의미하는 뜨개 기법 이름 (한글 / 영문 약어 둘 다 가능하면 둘 다)",
    "2. 어느 방향으로 실이 이동하는지, 어떤 코를 몇 코 모아뜨는지 등 구체적인 동작 설명",
    "3. 주의사항이나 자주 헷갈리는 포인트가 있다면 같이 설명",
    "",
    "아래는 내가 가지고 있는 사전/앱에서 자동으로 찾아낸 힌트들이야.",
    "필요하다면 참고해서 더 정확하게 설명해 줘.",
    "",
]

if abbr_hits:
    prompt_lines.append("▶ 텍스트에서 인식된 약어/기술 목록:")
    for h in abbr_hits:
        line = f"- {h['key']} / {h['name_en']} / {h['name_ko']}"
        if h["desc"]:
            line += f" — {h['desc']}"
        prompt_lines.append(line)
    prompt_lines.append("")

# 이미지 매칭 힌트도 추가
if uploaded_chart_img is not None:
    matches, _ = find_similar_icons(uploaded_chart_img, topk=5)
    if matches:
        prompt_lines.append("▶ 이미지로 매칭된 차트 기호 후보들:")
        for sim, icon in matches:
            label = icon.get("abbr") or "(이름 미입력)"
            desc = icon.get("desc") or ""
            line = f"- {label} (sheet: {icon['sheet']}, sim: {sim:.2f})"
            if desc:
                line += f" — {desc}"
            prompt_lines.append(line)
        prompt_lines.append("")

prompt_lines.append(
    "위 힌트는 100% 정답이 아닐 수도 있으니, 이미지 자체를 가장 우선으로 보고 판단해 줘."
)

full_prompt = "\n".join(prompt_lines)

st.text_area(
    "ChatGPT에 복사해서 붙여 넣을 프롬프트",
    value=full_prompt,
    height=260,
)

st.caption("※ 이 프롬프트를 복사한 뒤, ChatGPT에 이미지를 함께 올리고 붙여 넣어 사용하면 됩니다.")
st.divider()
st.page_link("HOME.py", label="⬅️ 홈으로")