# pages/2_뜨개_약어_사전.py
# 개별 영상 링크 1개(한국어 우선) + 정확도 강화 + 오버라이드 편집/저장

import os, re, json
import pandas as pd
import streamlit as st
from lib import parser

st.set_page_config(page_title="📘 뜨개 약어 사전", page_icon="📘", layout="wide")
st.title("📘 뜨개 약어 사전")
st.caption("사진 속 모든 약어가 포함됩니다. 각 항목에 **개별 영상 1개(한국어 우선)**가 하이퍼링크로 붙습니다. 잘못 매칭된 경우 우측 ‘검수/수정’에서 바로 고쳐 저장하세요.")

# ─────────────────────────────────────────────────────────────
# 설정
OVERRIDE_PATH = "lib/video_overrides.json"
DEFAULT_PLAYLISTS = [
    "https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ",
    "https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq",
]

# 사진 기반 필수/금지 키워드 규칙(정확도 강화)
MUST = {
    "1x1 rib": ["1x1", "rib"],
    "2x2 rib": ["2x2", "rib"],
    "garter": ["garter"],
    "stockinette": ["stockinette", "stocking", "st st", "st-st"],
    "k2tog": ["k2tog"],
    "p2tog": ["p2tog"],
    "ssk": ["ssk", "skp"],
    "ssp": ["ssp"],
    "m1l": ["m1l", "make 1 left"],
    "m1r": ["m1r", "make 1 right"],
    "yo": ["yarn over", "yo"],
    "ktbl": ["ktbl", "through the back loop", "tbl"],
    "ptbl": ["ptbl", "purl tbl", "through the back loop"],
    "cast on": ["cast on"],
    "bind off": ["bind off", "cast off"],
    "pick up": ["pick up"],
    "cable": ["cable"],
    "right cross": ["right cross", "rc"],
    "left cross": ["left cross", "lc"],
    "marker": ["stitch marker", "place marker", "slip marker", "pm", "sm"],
    "yarn front": ["yarn in front", "yfwd", "wyif"],
    "yarn back":  ["yarn in back", "ybk", "wyib"],
    "gauge": ["gauge"],
}
FORBID = {
    # 예: rib에서 yarn over 가 들어간 영상은 감점/탈락
    "1x1 rib": ["yarn over", "yo"],
    "2x2 rib": ["yarn over", "yo"],
    "garter": ["yarn over"],
    "stockinette": ["yarn over"],
    "k2tog": ["ssk", "ssp", "m1", "yarn over"],
    "p2tog": ["ssk", "ssp", "m1", "yarn over"],
    "ssk": ["k2tog", "m1", "yarn over"],
    "ssp": ["k2tog", "m1", "yarn over"],
    "m1l": ["k2tog", "ssk", "bind off"],
    "m1r": ["k2tog", "ssk", "bind off"],
}

# ─────────────────────────────────────────────────────────────
# 라이브러리 로드 + 전체 행 변환
LIB = parser.load_lib("symbols.json")
rows = []
for key, v in LIB.items():
    rows.append({
        "key": key,
        "약자(약어)": key,
        "용어(영문)": v.get("name_en",""),
        "한국어": v.get("name_ko",""),
        "설명": v.get("desc_ko",""),
        "aliases": [key] + v.get("aliases", []),
    })
base_df = pd.DataFrame(rows)

def norm(s): return (s or "").strip().lower()
base_df["_idx"] = (
    base_df["약자(약어)"].apply(norm) + " " +
    base_df["용어(영문)"].apply(norm) + " " +
    base_df["한국어"].apply(norm) + " " +
    base_df["aliases"].apply(lambda a: " ".join(norm(x) for x in a))
)

# ─────────────────────────────────────────────────────────────
# 오버라이드 로드/저장
def load_overrides(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except Exception:
        return {}

def save_overrides(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

OVR = load_overrides(OVERRIDE_PATH)

# ─────────────────────────────────────────────────────────────
# 재생목록에서 영상 수집
with st.sidebar:
    st.subheader("🎥 유튜브 재생목록")
    pls = st.text_area("한 줄에 하나씩", value="\n".join(DEFAULT_PLAYLISTS), height=90).strip().splitlines()
    fetch_btn = st.button("재생목록에서 영상 불러오기 / 갱신")
    reload_dict = st.button("🔁 용어 라이브러리 다시 로드")
    if reload_dict:
        parser._LIB = None
        parser._ALL_KEYS = None
        st.experimental_rerun()

@st.cache_data(show_spinner=True, ttl=60*60)
def fetch_videos_from_playlists(playlists: list[str]) -> pd.DataFrame:
    try:
        import yt_dlp
    except Exception:
        st.warning("yt-dlp가 설치되어 있지 않습니다. requirements.txt에 'yt-dlp' 추가 후 재실행하세요.")
        return pd.DataFrame(columns=["title","url","lower","has_korean"])
    vids = []
    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for pl in playlists:
            try:
                info = ydl.extract_info(pl, download=False)
                for e in (info or {}).get("entries", []) or []:
                    url = e.get("webpage_url") or e.get("url") or ""
                    if url and not url.startswith("http"):
                        url = f"https://www.youtube.com/watch?v={url}"
                    title = (e.get("title") or "").strip()
                    if not (url and title): 
                        continue
                    lower = title.lower()
                    has_korean = bool(re.search(r"[가-힣]", title))
                    vids.append({"title": title, "url": url, "lower": lower, "has_korean": has_korean})
            except Exception as ex:
                st.warning(f"재생목록 읽기 실패: {pl}\n{ex}")
    return pd.DataFrame(vids).drop_duplicates(subset=["url"])

video_df = fetch_videos_from_playlists(pls) if fetch_btn or "video_df" not in st.session_state else st.session_state["video_df"]
st.session_state["video_df"] = video_df

# ─────────────────────────────────────────────────────────────
# 스코어러(정확도 강화)
def choose_one_video(row, videos: pd.DataFrame, overrides: dict) -> tuple[str, list[dict]]:
    """오버라이드 > 스코어 기반 선택(한국어 우선) / 후보목록 반환"""
    key = row["key"]
    # 1) 오버라이드가 있으면 그대로
    if overrides.get(key):
        return overrides[key], []

    if videos is None or videos.empty:
        return "", []

    # 키워드 세트
    words = set()
    words.add(norm(row["약자(약어)"]))
    words.update(norm(a) for a in row["aliases"])
    words.update(w for w in re.split(r"[ /(),\-]+", norm(row["용어(영문)"])) if w)
    words = {w for w in words if w and len(w) >= 2}

    # 필수/금지
    must = set()
    forbid = set()
    for k, mlist in MUST.items():
        if k in words:
            must.update(mlist)
    for k, flist in FORBID.items():
        if k in words:
            forbid.update(flist)
    must = {m.lower() for m in must}
    forbid = {f.lower() for f in forbid}

    def score_row(vrow) -> int:
        t = vrow["lower"]
        # 필수 키워드가 하나도 없으면 탈락
        if must and not any(m in t for m in must):
            return -999
        s = 0
        # 정확도 가중치
        s += sum(3 for w in words if f" {w} " in f" {t} ")       # 완전어 매치
        s += sum(1 for w in words if w in t)                     # 부분어 매치
        s -= sum(3 for w in forbid if w in t)                    # 금지 키워드 감점
        # 언어 가중치: 한국어 우선
        s += 2 if vrow.get("has_korean") else 0
        return s

    scored = []
    for _, v in videos.iterrows():
        sc = score_row(v)
        if sc > 0:
            scored.append((sc, v["title"], v["url"]))
    scored.sort(key=lambda x: (-x[0], x[1]))
    top = scored[0][2] if scored else ""
    # 후보 상위 8개(검수용)
    cand = [{"title": t, "url": u, "score": s} for s, t, u in scored[:8]]
    return top, cand

# 매칭/후보 수집
selected_links, candidates = [], {}
for _, r in base_df.iterrows():
    link, cand = choose_one_video(r, video_df, OVR)
    selected_links.append(link)
    candidates[r["key"]] = cand

# ─────────────────────────────────────────────────────────────
# 검색 + 표(하이퍼링크) 렌더링
table_df = base_df[["약자(약어)", "용어(영문)", "한국어", "설명"]].copy()
table_df["영상"] = selected_links

c1, c2 = st.columns([2,1])
with c1:
    q = st.text_input("검색(예: m1l / cast on / 겉뜨기 / 게이지)", "")
with c2:
    only_with_video = st.checkbox("영상 있는 것만", value=False)

fdf = table_df.copy()
if q.strip():
    key = norm(q)
    fdf = fdf[base_df["_idx"].str.contains(key)].copy()
if only_with_video:
    fdf = fdf[fdf["영상"].astype(str).str.startswith("http")]

st.caption(f"총 용어: **{len(table_df)}** · 표시: **{len(fdf)}**")
st.data_editor(
    fdf[["약자(약어)","용어(영문)","한국어","설명","영상"]],
    use_container_width=True,
    hide_index=True,
    disabled=True,
    column_config={
        "영상": st.column_config.LinkColumn("영상", display_text="열기", max_chars=300)
    },
    num_rows="fixed",
    height=min(120 + len(fdf)*34, 5000),
)

# ─────────────────────────────────────────────────────────────
# 검수/수정 모드: 오버라이드 저장
st.markdown("---")
st.subheader("🛠 검수/수정 (오버라이드)")
st.caption("잘못 매칭된 항목은 여기서 원하는 영상을 선택하거나 직접 URL을 붙여 넣고 ‘저장’하세요. 저장하면 다음부터는 자동으로 이 링크가 사용됩니다.")

edited = False
for _, row in base_df.iterrows():
    k = row["key"]
    with st.expander(f"{row['약자(약어)']} · {row['용어(영문)']} · {row['한국어']}"):
        current = OVR.get(k, selected_links[_])
        st.write("현재 링크:", current or "없음")
        opts = candidates.get(k, [])
        titles = [f"[{c['score']}] {c['title']}" for c in opts]
        urls = [c["url"] for c in opts]
        pick = st.selectbox("후보에서 선택", ["(선택 안 함)"] + titles, index=0, key=f"pick_{k}")
        manual = st.text_input("직접 URL 입력(붙여넣기)", value=current or "", key=f"manual_{k}")
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("이 항목 저장", key=f"save_{k}"):
                new_url = ""
                if pick != "(선택 안 함)":
                    new_url = urls[titles.index(pick)]
                if manual.strip().startswith("http"):
                    new_url = manual.strip()
                if new_url:
                    OVR[k] = new_url
                elif k in OVR:   # 비우고 싶으면 삭제
                    del OVR[k]
                save_overrides(OVERRIDE_PATH, OVR)
                edited = True
        with col2:
            if st.button("오버라이드 제거", key=f"del_{k}"):
                if k in OVR:
                    del OVR[k]
                    save_overrides(OVERRIDE_PATH, OVR)
                    edited = True

if edited:
    st.success("저장되었습니다. 상단 표가 새 링크로 갱신됩니다.")
    st.experimental_rerun()