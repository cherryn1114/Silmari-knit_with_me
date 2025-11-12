# pages/2_뜨개_약어_사전.py
# 사진 속 모든 약어를 표로 보여주고, 개별 영상 링크 1개(한국어 우선)를 하이퍼링크로 삽입

import re
import pandas as pd
import streamlit as st
from lib import parser

st.set_page_config(page_title="📘 뜨개 약어 사전", page_icon="📘", layout="wide")
st.title("📘 뜨개 약어 사전")
st.caption("사진에 있던 모든 약어가 포함됩니다. 검색 가능하며, 각 항목에 관련 **개별 영상 링크 1개**(한국어 우선)가 붙습니다.")

# ─────────────────────────────────────────────────────────────
# 0) 영상 소스(유튜브 재생목록) — 제공해준 2개
DEFAULT_PLAYLISTS = [
    "https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ",
    "https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq",
]
with st.sidebar:
    st.subheader("🎥 유튜브 재생목록")
    pls = st.text_area(
        "한 줄에 하나씩 입력",
        value="\n".join(DEFAULT_PLAYLISTS),
        height=90,
    ).strip().splitlines()
    fetch_btn = st.button("재생목록에서 영상 불러오기 / 갱신")

# ─────────────────────────────────────────────────────────────
# 1) 용어 라이브러리(JSON) 로드 — 사진 속 약어들이 모두 들어있어야 함
LIB = parser.load_lib("symbols.json")   # 주의: "lib/..." 말고 파일명만!

# JSON → 표용 데이터 프레임
rows = []
for key, v in LIB.items():
    rows.append({
        "약자(약어)": key,
        "용어(영문)": v.get("name_en", ""),
        "한국어": v.get("name_ko", ""),
        "설명": v.get("desc_ko", ""),
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
# 2) yt-dlp로 개별 영상 제목/링크 수집(캐시)
@st.cache_data(show_spinner=True, ttl=60*60)
def fetch_videos_from_playlists(playlists: list[str]) -> pd.DataFrame:
    try:
        import yt_dlp  # pip install yt-dlp
    except Exception:
        st.warning("yt-dlp가 설치되어 있지 않습니다. requirements.txt에 'yt-dlp'를 추가하세요.")
        return pd.DataFrame(columns=["title", "url", "lower", "has_korean"])
    vids = []
    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for pl in playlists:
            try:
                info = ydl.extract_info(pl, download=False)
                for e in (info or {}).get("entries", []) or []:
                    # url이 영상 ID로만 올 수도 있음 → 정규화
                    url = e.get("webpage_url") or e.get("url") or ""
                    if url and not url.startswith("http"):
                        url = f"https://www.youtube.com/watch?v={url}"
                    title = (e.get("title") or "").strip()
                    if not (url and title):
                        continue
                    lower = title.lower()
                    # 제목에 한글 문자가 하나라도 있으면 한국어로 간주
                    has_korean = bool(re.search(r"[가-힣]", title))
                    vids.append({"title": title, "url": url, "lower": lower, "has_korean": has_korean})
            except Exception as ex:
                st.warning(f"재생목록 읽기 실패: {pl}\n{ex}")
    return pd.DataFrame(vids).drop_duplicates(subset=["url"])

video_df = fetch_videos_from_playlists(pls) if fetch_btn or "video_df" not in st.session_state else st.session_state["video_df"]
st.session_state["video_df"] = video_df

# ─────────────────────────────────────────────────────────────
# 3) 제목 매칭 규칙: 약어/동의어/영문명 키워드 포함 → 스코어링
BOOST = {
    # 핵심 기법 보정 키워드
    "k2tog": ["k2tog"],
    "p2tog": ["p2tog"],
    "ssk": ["ssk", "skp"],  # SKP로 올라간 영상 대응
    "ssp": ["ssp"],
    "m1l": ["m1l", "make 1 left"],
    "m1r": ["m1r", "make 1 right"],
    "yo": ["yo", "yarn over"],
    "ktbl": ["ktbl", "tbl", "through the back loop"],
    "ptbl": ["ptbl", "purl tbl", "through the back loop"],
    "garter": ["garter", "g-st"],
    "stockinette": ["stockinette", "stocking", "st st", "st-st"],
    "rib": ["rib", "1x1 rib", "2x2 rib", "r-st"],
    "gauge": ["gauge"],
    "cast on": ["cast on", "co", "long tail cast on", "backward loop"],
    "bind off": ["bind off", "cast off", "bo"],
    "pick up": ["pick up"],
    "cable": ["cable", "left cross", "right cross", "lc", "rc"],
    "slip": ["slip", "sl wyif", "sl wyib", "slip knitwise", "slip purlwise"],
    "marker": ["stitch marker", "place marker", "slip marker", "pm", "sm"],
    "yarn front": ["yarn in front", "wyif", "yfwd"],
    "yarn back": ["yarn in back", "wyib", "ybk"],
}

def choose_one_video(row, videos: pd.DataFrame) -> str:
    """각 항목에 대해 한국어 > 영어 순으로 1개 링크만 고른다. 없으면 빈 문자열."""
    if videos is None or videos.empty:
        return ""
    keys = set()
    # 약어, 동의어, 영문명에서 키워드 구성
    keys.add(norm(row["약자(약어)"]))
    keys.update(norm(a) for a in row["aliases"])
    keys.update(w for w in re.split(r"[ /(),\-]+", norm(row["용어(영문)"])) if w)
    # 보정 키워드 주입
    for k, boosts in BOOST.items():
        if k in keys or any(k in t for t in keys):
            keys.update(boosts)
    keys = {k for k in keys if k and len(k) >= 2}

    def score(title_lower: str) -> int:
        return sum(1 for k in keys if k in title_lower)

    # 스코어 계산
    videos = videos.copy()
    videos["score"] = videos["lower"].apply(score)
    cand = videos[videos["score"] > 0]
    if cand.empty:
        return ""
    # 1순위: 한국어(제목에 한글) 중 최고 점수
    ko = cand[cand["has_korean"]].sort_values(["score", "title"], ascending=[False, True])
    if not ko.empty:
        return ko.iloc[0]["url"]
    # 2순위: 전체 중 최고 점수
    best = cand.sort_values(["score", "title"], ascending=[False, True]).iloc[0]
    return best["url"]

# 1개 링크 선택
video_link = []
if not video_df.empty:
    for _, r in base_df.iterrows():
        video_link.append(choose_one_video(r, video_df))
else:
    video_link = [""] * len(base_df)

# ─────────────────────────────────────────────────────────────
# 4) 검색 + 표 렌더링 (하이퍼링크 1개)
table_df = base_df[["약자(약어)", "용어(영문)", "한국어", "설명"]].copy()
table_df["영상"] = video_link  # 개별 영상 URL 또는 빈칸

c1, c2 = st.columns([2,1])
with c1:
    q = st.text_input("검색 (예: m1l / cast on / 겉뜨기 / 게이지 등)", "")
with c2:
    show_cols = st.multiselect(
        "표시할 열",
        ["약자(약어)", "용어(영문)", "한국어", "설명", "영상"],
        default=["약자(약어)", "용어(영문)", "한국어", "설명", "영상"]
    )

fdf = table_df.copy()
if q.strip():
    key = norm(q)
    fdf = fdf[base_df["_idx"].str.contains(key)].copy()

# 하이퍼링크 컬럼(열기 버튼 형식)
link_cfg = {
    "영상": st.column_config.LinkColumn(
        "영상", help="개별 유튜브 영상 링크 (한국어 우선, 없으면 영어).", display_text="열기", max_chars=300
    )
}
st.data_editor(
    fdf[show_cols],
    use_container_width=True,
    hide_index=True,
    disabled=True,
    column_config=link_cfg,
    num_rows="fixed",
)

st.caption("※ 영상은 제공된 두 재생목록의 **개별 영상**을 제목-키워드로 자동 매칭해 1개만 연결합니다. 해당 영상이 없으면 빈칸으로 둡니다.")