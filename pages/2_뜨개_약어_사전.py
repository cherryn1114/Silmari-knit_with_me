# pages/2_뜨개_약어_사전.py
import re
import streamlit as st
import pandas as pd
from lib import parser

st.set_page_config(page_title="📘 뜨개 약어 사전", page_icon="📘", layout="wide")
st.title("📘 뜨개 약어 사전")
st.caption("영문 약어/영문 용어/한글로 검색하세요. 표의 ‘영상1/2/3’은 **개별 영상 링크**이며 클릭 즉시 이동합니다.")

# ─────────────────────────────────────────────────────────────
# 0) 기본 재생목록(너가 준 2개)
DEFAULT_PLAYLISTS = [
    "https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ",
    "https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq",
]

with st.sidebar:
    st.subheader("🎥 영상 소스(YouTube 재생목록)")
    playlists = st.text_area(
        "한 줄에 하나씩 재생목록 URL",
        value="\n".join(DEFAULT_PLAYLISTS),
        placeholder="https://youtube.com/playlist?list=XXXX\nhttps://youtube.com/playlist?list=YYYY",
        height=100,
    ).strip().splitlines()
    fetch_btn = st.button("재생목록에서 영상 불러오기/업데이트")

# ─────────────────────────────────────────────────────────────
# 1) 용어 라이브러리 로드 (사진 속 모든 약어는 lib/symbols.json에 이미 포함돼 있어야 함)
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
# 2) 재생목록 개별 영상 메타 수집 (yt-dlp)
@st.cache_data(show_spinner=True, ttl=60*60)
def fetch_videos_from_playlists(playlists: list[str]) -> pd.DataFrame:
    """
    playlists: 재생목록 URL 리스트
    return: DataFrame[title,url,lower]
    """
    try:
        import yt_dlp  # pip install yt-dlp
    except Exception:
        st.warning("yt-dlp가 설치되지 않았습니다. 터미널에서 `pip install yt-dlp` 실행 후 다시 시도하세요.")
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
                    # 일부 항목은 'url'에 비디오 ID만 들어오므로 보정
                    vid_url = e.get("url") or e.get("webpage_url") or ""
                    if vid_url and not vid_url.startswith("http"):
                        vid_url = f"https://www.youtube.com/watch?v={vid_url}"
                    title = (e.get("title") or "").strip()
                    if vid_url and title:
                        vids.append({"title": title, "url": vid_url, "lower": title.lower()})
            except Exception as ex:
                st.warning(f"재생목록을 읽는 중 오류: {pl}\n{ex}")

    df = pd.DataFrame(vids).drop_duplicates(subset=["url"])
    return df

# 최초/업데이트 로드
if fetch_btn or "video_df" not in st.session_state:
    st.session_state["video_df"] = fetch_videos_from_playlists(playlists)
video_df = st.session_state["video_df"]

# ─────────────────────────────────────────────────────────────
# 3) 약어-영상 제목 매칭 규칙
BOOST = {
    # 늘림/줄임/기본기
    "k2tog": ["k2tog"],
    "p2tog": ["p2tog"],
    "ssk": ["ssk", "skp"],
    "ssp": ["ssp"],
    "m1l": ["m1l", "make 1 left", "left increase"],
    "m1r": ["m1r", "make 1 right", "right increase"],
    "yo": ["yo", "yarn over"],

    # 꼬아뜨기/뒤다리
    "ktbl": ["ktbl", "tbl", "through the back loop"],
    "ptbl": ["ptbl", "purl tbl", "through the back loop"],

    # 조직/기본무늬
    "garter": ["garter"],
    "stockinette": ["stockinette", "stocking"],
    "rib": ["rib", "1x1 rib", "2x2 rib"],

    # 기타
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
    """약어/동의어/영문/한글 키워드로 영상 제목을 스코어링해 상위 topk 반환"""
    if videos.empty:
        return []
    keys = set()
    keys.add(norm(row["약자(약어)"]))
    keys.update([w for w in re.split(r"[ /(),-]+", row["용어(영문)"].lower()) if w])
    keys.update([norm(a) for a in row["aliases"]])
    # 한글 주요어도 합치기 (간단 선택)
    for k in ["늘리", "줄이", "겉뜨", "안뜨", "꽈배", "교차", "마커", "게이지"]:
        if k in row["한국어"]:
            # 대응 영문 키워드 추가
            if k == "늘리": keys.update(["increase", "m1", "inc"])
            if k == "줄이": keys.update(["decrease", "dec", "tog"])
            if k == "겉뜨": keys.update(["knit"])
            if k == "안뜨": keys.update(["purl"])
            if k == "꽈배" or k == "교차": keys.update(["cable", "cross"])
            if k == "마커": keys.update(["marker"])
            if k == "게이지": keys.update(["gauge"])

    # 보정 사전
    for bkey, boosts in BOOST.items():
        if any(bkey in k for k in keys):
            keys.update(boosts)

    keys = [k for k in keys if k and len(k) >= 2]

    def score(title_lower: str) -> int:
        return sum(1 for k in keys if k in title_lower)

    scored = []
    for _, v in videos.iterrows():
        s = score(v["lower"])
        if s > 0:
            scored.append((s, v["title"], v["url"]))
    scored.sort(key=lambda x: (-x[0], x[1]))
    top = scored[:topk]
    return [{"title": t, "url": u} for _, t, u in top]

# 매칭 실행
df = base_df.copy()
if not video_df.empty:
    df["matches"] = df.apply(lambda r: collect_matches(r, video_df), axis=1)
else:
    df["matches"] = [[] for _ in range(len(df))]

# ─────────────────────────────────────────────────────────────
# 4) 검색 + 표(클릭 가능한 하이퍼링크) 구성
c1, c2 = st.columns([2,1])
with c1:
    q = st.text_input("검색 (예: m1l / cast on / 겉뜨기 / 게이지 등)", "")
with c2:
    show_cols = st.multiselect(
        "표시할 열",
        ["약자(약어)", "용어(영문)", "한국어", "설명", "영상1", "영상2", "영상3"],
        default=["약자(약어)", "용어(영문)", "한국어", "설명", "영상1", "영상2", "영상3"]
    )

f = df.copy()
if q.strip():
    key = norm(q)
    f = f[f["_idx"].str.contains(key)]

# 영상 링크 컬럼 3개 생성 (개별 영상 하이퍼링크)
def nth_link(vlist, n):
    if not vlist or len(vlist) < n: 
        return "", ""
    v = vlist[n-1]
    return v.get("title","video"), v.get("url","")

titles1, urls1, titles2, urls2, titles3, urls3 = [], [], [], [], [], []
for vs in f["matches"].tolist():
    t1, u1 = nth_link(vs, 1)
    t2, u2 = nth_link(vs, 2)
    t3, u3 = nth_link(vs, 3)
    titles1.append(t1); urls1.append(u1)
    titles2.append(t2); urls2.append(u2)
    titles3.append(t3); urls3.append(u3)

f = f.drop(columns=["matches", "_idx", "aliases"])
f["영상1 제목"] = titles1; f["영상1"] = urls1
f["영상2 제목"] = titles2; f["영상2"] = urls2
f["영상3 제목"] = titles3; f["영상3"] = urls3

# 표시 컬럼 선택/정렬
base_cols = ["약자(약어)", "용어(영문)", "한국어", "설명"]
video_cols = ["영상1 제목","영상1","영상2 제목","영상2","영상3 제목","영상3"]
ordered = []
for c in ["약자(약어)", "용어(영문)", "한국어", "설명", "영상1", "영상2", "영상3"]:
    if c in ["영상1","영상2","영상3"]:
        # 제목-링크 쌍을 표에 함께 보여주고 싶으면 제목 컬럼도 포함
        idx = int(c[-1])
        tcol = f"영상{idx} 제목"
        if tcol not in ordered: ordered.append(tcol)
        if c not in ordered: ordered.append(c)
    else:
        if c not in ordered: ordered.append(c)

# 최종 표
table = f[ordered].copy()

# 🔗 링크가 표에서 바로 클릭되도록 LinkColumn 사용
link_cfg = {
    "영상1": st.column_config.LinkColumn("영상1", display_text="열기"),
    "영상2": st.column_config.LinkColumn("영상2", display_text="열기"),
    "영상3": st.column_config.LinkColumn("영상3", display_text="열기"),
}

# 표시할 열만 필터
table = table[[c for c in ordered if c in show_cols or c.startswith("영상") and c.replace(" 제목","") in show_cols]]

st.write(f"검색 결과: **{len(table)}**개")
st.dataframe(table, use_container_width=True, hide_index=True, column_config=link_cfg)

st.divider()
st.caption("※ ‘영상1/2/3’은 제공된 재생목록에서 제목-키워드로 자동 매칭된 개별 영상입니다. 필요시 사이드바에서 재생목록을 바꾸고 ‘불러오기’ 버튼을 눌러 갱신하세요.")