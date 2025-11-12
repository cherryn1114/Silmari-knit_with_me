import re
import streamlit as st
import pandas as pd
from lib import parser

st.set_page_config(page_title="📘 뜨개 약어 사전", page_icon="📘", layout="wide")
st.title("📘 뜨개 약어 사전")
st.caption("영문 약어/영문 용어/한글 아무거나로 검색하세요. 각 항목에 관련 **개별 영상 링크**가 붙습니다.")

# ─────────────────────────────────────────────────────────────
# 0) 환경: 플레이리스트(기본값: 네가 준 2개)
DEFAULT_PLAYLISTS = [
    "https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ",
    "https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq",
]

with st.sidebar:
    st.subheader("🎥 영상 소스(YouTube 재생목록)")
    pls = st.text_area(
        "한 줄에 하나씩 재생목록 URL",
        value="\n".join(DEFAULT_PLAYLISTS),
        placeholder="https://youtube.com/playlist?list=XXXX\nhttps://youtube.com/playlist?list=YYYY",
        height=100,
    ).strip().splitlines()
    fetch_btn = st.button("재생목록에서 영상 불러오기(또는 업데이트)")

# ─────────────────────────────────────────────────────────────
# 1) 용어 라이브러리 로드
LIB = parser.load_lib("symbols.json")   # 주의: "lib/..." 말고 "symbols.json"만!
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

# 검색 인덱스
def norm(s): return (s or "").strip().lower()
base_df["_idx"] = (
    base_df["약자(약어)"].apply(norm) + " " +
    base_df["용어(영문)"].apply(norm) + " " +
    base_df["한국어"].apply(norm) + " " +
    base_df["aliases"].apply(lambda a: " ".join([norm(x) for x in a]))
)

# ─────────────────────────────────────────────────────────────
# 2) 재생목록에서 영상 수집 (yt-dlp)
#   - codespaces/streamlit 서버에서만 실행됨. 실패하면 기존 캐시 사용.
@st.cache_data(show_spinner=True, ttl=60*60)
def fetch_videos_from_playlists(playlists: list[str]) -> pd.DataFrame:
    """
    playlists: 재생목록 URL 리스트
    return: DataFrame[title,url,lower]
    """
    try:
        import yt_dlp  # pip install yt-dlp
    except Exception as e:
        st.warning("yt-dlp가 설치되지 않았습니다. `pip install yt-dlp` 후 다시 시도하세요.")
        return pd.DataFrame(columns=["title","url","lower"])

    vids: list[dict] = []
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,  # 빠르게 메타데이터만
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for pl in playlists:
            try:
                info = ydl.extract_info(pl, download=False)
                entries = info.get("entries", []) if info else []
                for e in entries:
                    # 일부 항목은 'url'이 video id로 들어옵니다.
                    vid_url = e.get("url") or e.get("webpage_url") or ""
                    if vid_url and not vid_url.startswith("http"):
                        vid_url = f"https://www.youtube.com/watch?v={vid_url}"
                    title = e.get("title") or ""
                    if vid_url and title:
                        vids.append({"title": title, "url": vid_url, "lower": title.lower()})
            except Exception as ex:
                st.warning(f"재생목록을 읽는 중 오류: {pl}\n{ex}")

    df = pd.DataFrame(vids).drop_duplicates(subset=["url"])
    return df

video_df = fetch_videos_from_playlists(pls) if fetch_btn or "video_df" not in st.session_state else st.session_state["video_df"]
st.session_state["video_df"] = video_df

# ─────────────────────────────────────────────────────────────
# 3) 간단 매칭 규칙
#   - 약어/동의어/영문명을 제목에 포함하면 매칭
#   - 추가 키워드(보정) 사전으로 정확도 향상
BOOST = {
    # 줄임/오타 변형과 대표 키워드 보정
    "k2tog": ["k2tog"],
    "p2tog": ["p2tog"],
    "ssk": ["ssk", "skp"],  # 영상에 SKP라고 올라간 경우
    "ssp": ["ssp"],
    "m1l": ["m1l", "make 1 left"],
    "m1r": ["m1r", "make 1 right"],
    "yo": ["yo", "yarn over"],
    "ktbl": ["ktbl", "tbl", "through the back loop"],
    "ptbl": ["ptbl", "purl tbl", "through the back loop"],
    "garter": ["garter"],
    "stockinette": ["stockinette","stocking"],
    "rib": ["rib","1x1 rib","2x2 rib"],
    "gauge": ["gauge"],
    "cast on": ["cast on","co","long tail cast on","backward loop"],
    "bind off": ["bind off","cast off","bo"],
    "pick up": ["pick up"],
    "cable": ["cable","left cross","right cross","lc","rc"],
    "slip": ["slip","sl wyif","sl wyib","slip knitwise","slip purlwise"],
    "marker": ["stitch marker","place marker","slip marker","pm","sm"],
    "yarn front": ["yarn in front","wyif","yfwd"],
    "yarn back": ["yarn in back","wyib","ybk"],
}

def collect_matches(row, videos: pd.DataFrame, topk=4):
    if videos.empty:
        return []
    keys = set()
    # 기본: 약어/영문/한글/별칭에서 단어 추출
    keys.update([norm(row["약자(약어)"])])
    keys.update([w.strip().lower() for w in re.split(r"[ /(),-]+", row["용어(영문)"]) if w])
    keys.update([norm(a) for a in row["aliases"]])

    # 보정 사전
    for k, boosts in BOOST.items():
        if k in keys or any(k in t for t in keys):
            keys.update(boosts)

    keys = [k for k in keys if k and len(k) >= 2]
    # 스코어 = 제목에 포함되는 키워드 개수
    def score(title_lower: str) -> int:
        return sum(1 for k in keys if k in title_lower)

    scored = []
    for _, v in videos.iterrows():
        s = score(v["lower"])
        if s > 0:
            scored.append((s, v["title"], v["url"]))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [{"title": t, "url": u} for _, t, u in scored[:topk]]

# 각 항목에 videos 매칭
if not video_df.empty:
    base_df["videos"] = base_df.apply(lambda r: collect_matches(r, video_df), axis=1)
else:
    base_df["videos"] = [[] for _ in range(len(base_df))]

# ─────────────────────────────────────────────────────────────
# 4) 검색 + 표 + 카드(영상 바로가기)
c1, c2 = st.columns([2,1])
with c1:
    q = st.text_input("검색 (예: m1l / cast on / 겉뜨기 / 게이지 등)", "")
with c2:
    show_cols = st.multiselect(
        "표시할 열",
        ["약자(약어)", "용어(영문)", "한국어", "설명"],
        default=["약자(약어)", "용어(영문)", "한국어", "설명"],
    )

fdf = base_df.copy()
if q.strip():
    key = norm(q)
    fdf = fdf[fdf["_idx"].str.contains(key)]
fdf = fdf[["약자(약어)", "용어(영문)", "한국어", "설명", "videos"]]

st.write(f"검색 결과: **{len(fdf)}**개")
st.dataframe(fdf[show_cols], use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("🔗 항목별 영상 바로가기")

for _, r in fdf.iterrows():
    with st.expander(f"{r['약자(약어)']} · {r['용어(영문)']} · {r['한국어']}"):
        vids = r["videos"] or []
        if not vids:
            st.write("관련 영상을 찾지 못했습니다. (재생목록 업데이트 후 다시 시도)")
        else:
            for v in vids:
                st.markdown(f"- [{v['title']}]({v['url']})")

st.caption("※ 유튜브 재생목록의 영상 제목과 약어/동의어를 비교해 자동 매칭합니다. 제목 표기와 약어가 다르면 수동으로 `BOOST`/`aliases`를 보강하면 정확도가 올라갑니다.")