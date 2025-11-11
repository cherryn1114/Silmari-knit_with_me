import streamlit as st
import pandas as pd

st.set_page_config(page_title="📘 뜨개 약어 사전", page_icon="📘", layout="wide")
st.title("📘 뜨개 약어 사전")
st.caption("검색창에 영문 약어/영문 용어/한글 아무거나 입력하세요 (예: m1l, 겉뜨기, cast on, 게이지 등).")

# ----- 데이터 정의 (영상 링크 포함) -----
DATA = [
    {"abbr":"k", "term_en":"Knit", "term_ko":"겉뜨기", "desc":"바늘 앞쪽에서 실을 뒤로 보내며 뜨는 기본 뜨기.", "videos":[{"title":"Knit stitch tutorial", "url":"https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ"}]},
    {"abbr":"p", "term_en":"Purl", "term_ko":"안뜨기", "desc":"바늘 뒤쪽에서 실을 앞으로 보내며 뜨는 기본 뜨기.", "videos":[{"title":"Purl stitch tutorial", "url":"https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ"}]},
    {"abbr":"sl", "term_en":"Slip", "term_ko":"걸러뜨기 (코를 그냥 옆 바늘로 옮기는 것)", "desc":"코를 뜨지 않고 옆 바늘로 옮기는 기법.", "videos":[{"title":"Slip stitch knitting", "url":"https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ"}]},
    {"abbr":"yo", "term_en":"Yarn Over", "term_ko":"바늘 비우기, 구멍뜨기, 걸기코", "desc":"실을 바늘 위로 걸어 1코를 늘리는 기법.", "videos":[{"title":"Yarn over (YO) knitting", "url":"https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ"}]},
    {"abbr":"PU", "term_en":"Pick up", "term_ko":"코 줍기", "desc":"원단 모서리 등에서 코를 주워 새 코를 만드는 기법.", "videos":[{"title":"Pick up stitches edge knitting", "url":"https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"tbl (ktbl)", "term_en":"Through the back loop (knit)", "term_ko":"꼬아 뜨기 (돌려 뜨기)", "desc":"코의 뒤쪽 다리를 걸어 겉뜨기.", "videos":[{"title":"Knit through back loop ktbl", "url":"https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"P tbl", "term_en":"Purl through the back loop", "term_ko":"코의 뒤를 걸어 안뜨기", "desc":"안뜨기 방식으로 뒤다리를 걸어 안뜨기.", "videos":[{"title":"Purl through back loop ptbl", "url":"https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"K1-b", "term_en":"Knit 1 stitch through the back loop", "term_ko":"겉뜨기로 꼬아 뜨기 1코", "desc":"한 코를 뒤다리로 겉뜨기.", "videos":[{"title":"K1 tbl knitting", "url":"https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"RC", "term_en":"Right Cross", "term_ko":"오른코 교차뜨기 (꽈배기 바늘 이용)", "desc":"오른쪽으로 두 코 혹은 네 코를 겹쳐 뜨는 꽈배기 기법.", "videos":[{"title":"Right cross cable knitting", "url":"https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"LC", "term_en":"Left Cross", "term_ko":"왼코 교차뜨기 (꽈배기 바늘 이용)", "desc":"왼쪽으로 두 코 혹은 네 코를 겹쳐 뜨는 꽈배기 기법.", "videos":[{"title":"Left cross cable knitting", "url":"https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"CO", "term_en":"Cast on", "term_ko":"코 만들기, 코 잡기", "desc":"작품을 시작하기 위해 바늘에 코를 만드는 작업.", "videos":[{"title":"Cast on methods knitting", "url":"https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ"}]},
    {"abbr":"Backward Loop CO", "term_en":"Backward Loop Cast on (=Thumb Method Cast on)", "term_ko":"감아코", "desc":"아이디얼 방식으로 엄지로 실을 감아 코를 만드는 느낌.", "videos":[{"title":"Backward loop cast on knitting", "url":"https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"Cast off", "term_en":"Cast off", "term_ko":"코 막기, 코 마무리", "desc":"완성 후 코를 정리해 내리는 마감 작업.", "videos":[{"title":"Bind off cast off knitting", "url":"https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ"}]},
    {"abbr":"BO", "term_en":"Bind off", "term_ko":"덮어 씌워 코 막기, 덮어씌워 코 마무리", "desc":"두 코를 떠서 첫 코 위로 덮어가며 줄여나가는 마감 방식.", "videos":[{"title":"Standard bind off knitting", "url":"https://youtube.com/playlist?list=PLp5XrSgnenszb2E_yfQ-X2KFwHsUhRTyJ"}]},
    {"abbr":"Kwise", "term_en":"Knit-wise (way)", "term_ko":"겉뜨기로 코 막기/겉 방향", "desc":"코를 겉뜨기 방향으로 바늘에 건다.", "videos":[{"title":"Insert knitwise slip knitwise knitting", "url":"https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"Pwise", "term_en":"Purl-wise (way)", "term_ko":"안뜨기 방향", "desc":"코를 안뜨기 방향으로 바늘에 건다.", "videos":[{"title":"Insert purlwise slip purlwise knitting", "url":"https://youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"st / sts", "term_en":"Stitch / Stitches", "term_ko":"코, 코들 (단수·복수)", "desc":"편물의 한 코 또는 여러 코.", "videos":[]},
    {"abbr":"Row", "term_en":"Row", "term_ko":"단", "desc":"평면 편물의 가로 한 줄.", "videos":[]},
    {"abbr":"RS", "term_en":"Right Side", "term_ko":"겉면, 앞면", "desc":"작품의 겉면(앞면).", "videos":[]},
    {"abbr":"WS", "term_en":"Wrong Side", "term_ko":"뒷면, 안쪽면", "desc":"작품의 안쪽면.", "videos":[]},
    {"abbr":"Lp / Lps", "term_en":"Loop / Loops", "term_ko":"첫 시작코 만들 때 고리", "desc":"코를 이루는 실의 고리.", "videos":[]},
    {"abbr":"gauge", "term_en":"Gauge", "term_ko":"게이지 (10 cm 내 코·단수)", "desc":"사이즈에 영향을 주는 코/단수.", "videos":[{"title":"How to measure gauge knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"pattern", "term_en":"Pattern", "term_ko":"도안", "desc":"작품 만드는 지시서.", "videos":[]},
    {"abbr":"MC", "term_en":"Main Color", "term_ko":"메인 컬러 (주요 컬러)", "desc":"주요 실 색.", "videos":[]},
    {"abbr":"CC", "term_en":"Contrasting Color", "term_ko":"배색 컬러", "desc":"보조 색실(배색).", "videos":[]},
    {"abbr":"Cable", "term_en":"Cable", "term_ko":"꽈배기 무늬", "desc":"코를 교차시켜 생기는 꼬임 무늬.", "videos":[{"title":"Cable knitting basics", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"M", "term_en":"Marker", "term_ko":"마커, 단수링, 표시링", "desc":"구간 표시 도구.", "videos":[{"title":"How to use stitch markers knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"SM / M", "term_en":"Slip Marker", "term_ko":"단수링을 옆 바늘로 옮기기", "desc":"마커를 옆 바늘로 옮기는 기법.", "videos":[{"title":"Slip marker SM knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"PM", "term_en":"Place Marker", "term_ko":"단수링 끼우기", "desc":"해당 지점에 마커 설치.", "videos":[{"title":"Place a stitch marker PM knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"yb / ybk / wyib", "term_en":"Yarn in back / yarn to the back", "term_ko":"실을 뒤로 보낸다", "desc":"겉뜨기 작업 상태로 실 위치를 뒤로 이동.", "videos":[{"title":"Yarn in back YIB knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"yf / yfwd / wyif", "term_en":"Yarn to the front", "term_ko":"실을 앞으로 보낸다", "desc":"안뜨기 작업 상태로 실 위치를 앞으로 이동.", "videos":[{"title":"Yarn in front YIF knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"Circular needle", "term_en":"Circular needle", "term_ko":"줄바늘(대바늘)", "desc":"두 바늘이 케이블로 연결된 바늘.", "videos":[]},
    {"abbr":"dpn", "term_en":"Double-point needle", "term_ko":"양끝이 뾰족한 바늘 (원통뜨기)", "desc":"양끝이 뾰족한 바늘 세트.", "videos":[]},
    {"abbr":"Cn", "term_en":"Cable needle", "term_ko":"꽈배기 바늘", "desc":"교차/케이블뜨기 시 보조 바늘.", "videos":[]},
    {"abbr":"holder", "term_en":"Holder", "term_ko":"어깨핀, 막음핀, 마감핀, 코막음핀", "desc":"코를 임시로 보관하는 도구.", "videos":[]},
    {"abbr":"darning needle", "term_en":"Darning/tapestry needle", "term_ko":"돗바늘", "desc":"실 마감/꿰매기에 쓰는 굵은 바늘.", "videos":[]},
    {"abbr":"St-st", "term_en":"Stockinette Stitch (US) / Stocking Stitch (UK)", "term_ko":"메리야스뜨기", "desc":"겉·안 반복 또는 연속 겉뜨기.", "videos":[]},
    {"abbr":"Rib (r-st)", "term_en":"Ribbing", "term_ko":"고무뜨기", "desc":"겉/안 반복으로 탄성 무늬.", "videos":[]},
    {"abbr":"1×1 Rib", "term_en":"One by one ribbing", "term_ko":"1코 고무뜨기", "desc":"겉뜨기 1코 + 안뜨기 1코 반복.", "videos":[]},
    {"abbr":"2×2 Rib", "term_en":"Two by two ribbing", "term_ko":"2코 고무뜨기", "desc":"겉뜨기 2코 + 안뜨기 2코 반복.", "videos":[]},
    {"abbr":"G-st", "term_en":"Garter stitch", "term_ko":"가터뜨기 (이랑뜨기)", "desc":"1단씩 겉뜨기 반복.", "videos":[]},
    {"abbr":"Moss st", "term_en":"Moss stitch", "term_ko":"멍석뜨기", "desc":"겉뜨기/안뜨기가 번갈아 나오는 조직.", "videos":[]},
    {"abbr":"Inc", "term_en":"Increase", "term_ko":"코 늘리기", "desc":"코를 하나 늘리는 기법.", "videos":[{"title":"Increase knitting tutorial", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"M1", "term_en":"Make 1", "term_ko":"1코 늘리기", "desc":"한 코를 새로운 코로 만든다.", "videos":[{"title":"Make 1 knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"M1R", "term_en":"Make one Right", "term_ko":"오른코 늘려뜨기", "desc":"겉코의 오른쪽에서 1코 늘리기.", "videos":[{"title":"M1R increase knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"M1L", "term_en":"Make one Left", "term_ko":"왼코 늘려뜨기", "desc":"겉코의 왼쪽에서 1코 늘리기.", "videos":[{"title":"M1L increase knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"Tog", "term_en":"Together", "term_ko":"모아뜨기", "desc":"겉뜨기로 2코 혹은 더 많은 코를 한 번에 뜨기.", "videos":[{"title":"tog together knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"k2tog", "term_en":"Knit 2 stitches together", "term_ko":"겉뜨기로 2코 모아뜨기", "desc":"왼쪽 2코를 한 번에 겉뜨기.", "videos":[{"title":"k2tog knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"p2tog", "term_en":"Purl 2 stitches together", "term_ko":"안뜨기로 2코 모아뜨기", "desc":"왼쪽 2코를 한 번에 안뜨기.", "videos":[{"title":"p2tog knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"SKP (=SSK)", "term_en":"Slip, Knit, pass the slipped stitch over (=Slip, Slip, Knit)", "term_ko":"오른코 겹쳐 2코 모아뜨기 (겉코로 오른코 1코 줄이기)", "desc":"SSK와 동일 결과.", "videos":[{"title":"ssk knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
    {"abbr":"SSP", "term_en":"Slip, Slip, Purl", "term_ko":"오른코 겹쳐 2코 모아 안뜨기 (안코로 오른코 1코 줄이기)", "desc":"", "videos":[{"title":"ssp knitting", "url":"https://www.youtube.com/playlist?list=PLtqSRloqJqzodilL7rTKkd6BwS8RvVpTq"}]},
]

# ----- 가공: 검색용 토큰 생성 -----
def normalize(s: str) -> str:
    return (s or "").strip().lower()

df = pd.DataFrame(DATA)
df["abbr_norm"] = df["abbr"].apply(normalize)
df["en_norm"] = df["term_en"].apply(normalize)
df["ko_norm"] = df["term_ko"].apply(normalize)
df["all_norm"] = df["abbr_norm"] + " " + df["en_norm"] + " " + df["ko_norm"]

# ----- 검색 UI -----
c1, c2 = st.columns([2,1])
with c1:
    q = st.text_input("검색 (예: m1l / cast on / 겉뜨기 / 게이지 등)", "")
with c2:
    show_cols = st.multiselect(
        "표시할 열",
        ["약자(약어)", "용어(영문)", "한국어", "설명", "영상 링크"],
        default=["약자(약어)", "용어(영문)", "한국어", "설명", "영상 링크"]
    )

# ----- 필터링 -----
if q.strip():
    key = normalize(q)
    mask = df["all_norm"].str.contains(key)
    fdf = df[mask].copy()
else:
    fdf = df.copy()

# ----- 영상 링크 컬럼 생성 -----
def make_video_link(vlist):
    if not vlist:
        return ""
    # 첫 링크만 표시 (여러 영상 가능)
    return f"[{vlist[0]['title']}]({vlist[0]['url']})"

fdf["영상 링크"] = fdf["videos"].apply(make_video_link)

# ----- 표 컬럼 정리 -----
fdf = fdf.rename(columns={
    "abbr": "약자(약어)",
    "term_en": "용어(영문)",
    "term_ko": "한국어",
    "desc": "설명",
})
fdf = fdf[show_cols]

st.write(f"검색 결과: **{len(fdf)}**개")
st.dataframe(fdf, use_container_width=True, hide_index=True)

st.divider()
st.caption("※ 본 사전은 과제 데모용으로 구성되었습니다. 영상 링크는 제공된 유튜브 플레이리스트 기반이며, 실제 패턴/표기와 다를 수 있습니다.")