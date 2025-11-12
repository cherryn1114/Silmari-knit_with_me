# pages/2_뜨개_약어_사전.py
# 표 형식 + 개별 영상 하이퍼링크(클릭 즉시 이동)
import re
import pandas as pd
import streamlit as st
from lib import parser

st.set_page_config(page_title="📘 뜨개 약어 사전", page_icon="📘", layout="wide")
st.title("📘 뜨개 약어 사전")
st.caption("영문 약어/영문 용어/한글로 검색하세요. 각 항목에 관련 **개별 영상 링크**가 표에 들어갑니다.")

# ─────────────────────────────────────────────────────────────
# 0) 영상 소스(유튜브 재생목록)
DEFAULT_PLAYLISTS = [
    "https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ",
    "https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq",
]
with st.sidebar:
    st.subheader("🎥 유튜브 재생목록")
    pls = st.text_area(
        "한 줄에 하나씩 입력",
        value="\n".join(DEFAULT_PLAYLISTS),
        height=100,
        placeholder="https://youtube.com/playlist?list=XXXX\nhttps://youtube.com/playlist?list=YYYY",
    ).strip().splitlines()
    fetch_btn = st.button("재생목록에서 영상 불러오기 / 업데이트")

# ─────────────────────────────────────────────────────────────
# 1) 약어 라이브러리 로드 (사진 속 모든 약어는 lib/symbols.json에 들어있어야 함)
LIB = parser.load_lib("symbols.json")   # 주의: "lib/..." 말고 파일명만!
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
# 2) yt-dlp로 재생목록의 개별 영상 제목/링크 가져오기 (캐시)
@st.cache_data(show_spinner=True, ttl=60*60)
def fetch_videos_from_playlists(playlists: list[str]) -> pd.DataFrame:
    try:
        import yt_dlp  # pip install yt-dlp
    except Exception:
        st.warning("yt-dlp가 설치되어 있지 않습니다. requirements.txt에 'yt-dlp' 추가 후 다시 시도하세요.")
        return pd.DataFrame(columns=["title", "url", "lower"])
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
                    title = e.get("title") or ""
                    if url and title:
                        vids.append({"title": title, "url": url, "lower": title.lower()})
            except Exception as ex:
                st.warning(f"재생목록 읽기 실패: {pl}\n{ex}")
    df = pd.DataFrame(vids).drop_duplicates(subset=["url"])
    return df

video_df = fetch_videos_from_playlists(pls) if fetch_btn or "video_df" not in st.session_state else st.session_state["video_df"]
st.session_state["video_df"] = video_df

# ─────────────────────────────────────────────────────────────
# 3) 영상 매칭 규칙 (제목에 약어/동의어/영문명 키워드가 들어가면 매칭)
BOOST = {
    # 대표 증가/감소/기본
    "k2tog": ["k2tog"],
    "p2tog": ["p2tog"],
    "ssk": ["ssk", "skp"],  # 영상이 SKP로 올라간 경우 커버
    "ssp": ["ssp"],
    "m1l": ["m1l", "make 1 left"],
    "m1r": ["m1r", "make 1 right"],
    "yo": ["yo", "yarn over"],
    "ktbl": ["ktbl", "tbl", "through the back loop"],
    "ptbl": ["ptbl", "purl tbl", "through the back loop"],
    "garter": ["garter"],
    "stockinette": ["stockinette", "stocking", "st st"],
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

def collect_matches(row, videos: pd.DataFrame, topk=3):
    if videos.empty: return ["", "", ""]
    keys = set()
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

    scored = []
    for _, v in videos.iterrows():
        s = score(v["lower"])
        if s > 0:
            scored.append((s, v["title"], v["url"]))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out = [u for _, _, u in scored[:topk]]
    # 항상 3칸 유지
    while len(out) < topk: out.append("")
    return out[:topk]

# 매칭 수행
video1, video2, video3 = [], [], []
if not video_df.empty:
    for _, r in base_df.iterrows():
        v1, v2, v3 = collect_matches(r, video_df, topk=3)
        video1.append(v1); video2.append(v2); video3.append(v3)
else:
    video1 = [""]*len(base_df); video2 = [""]*len(base_df); video3 = [""]*len(base_df)

# 표 데이터 구성 (하이퍼링크 컬럼 3개)
table_df = base_df[["약자(약어)", "용어(영문)", "한국어", "설명"]].copy()
table_df["영상1"] = video1
table_df["영상2"] = video2
table_df["영상3"] = video3

# ─────────────────────────────────────────────────────────────
# 4) 검색 → 표 렌더링(링크 클릭 가능)
c1, c2 = st.columns([2,1])
with c1:
    q = st.text_input("검색 (예: m1l / cast on / 겉뜨기 / 게이지 등)", "")
with c2:
    show_cols = st.multiselect(
        "표시할 열",
        ["약자(약어)", "용어(영문)", "한국어", "설명", "영상1", "영상2", "영상3"],
        default=["약자(약어)", "용어(영문)", "한국어", "설명", "영상1", "영상2", "영상3"]
    )

fdf = table_df.copy()
if q.strip():
    key = norm(q)
    idx = base_df["_idx"].str.contains(key)
    fdf = fdf[idx].copy()

# Streamlit의 data_editor + LinkColumn 으로 "클릭 가능한 링크" 표 구현
link_cols = {}
for col in ["영상1", "영상2", "영상3"]:
    link_cols[col] = st.column_config.LinkColumn(
        col, help="영상 링크", validate="^https?://.*", max_chars=300, display_text="열기"
    )

st.data_editor(
    fdf[show_cols],
    use_container_width=True,
    hide_index=True,
    disabled=True,  # 보기 전용
    column_config=link_cols,
    num_rows="fixed",
)

st.caption("※ 링크는 제공된 유튜브 재생목록의 **개별 영상**을 제목-키워드로 매칭해 자동 부여됩니다. 필요 시 사이드바에서 재생목록을 바꾸고 ‘불러오기’를 눌러 업데이트하세요.")