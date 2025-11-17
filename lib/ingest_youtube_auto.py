# lib/ingest_youtube_auto.py
# 사용법:
#   python lib/ingest_youtube_auto.py https://youtube.com/playlist?list=PLexrkqgKCXvC5P6B5Zggyz44M6kAU10P1
# 결과:
#   lib/symbols_extra.json 에 새로운 약어 자동 추가

import sys, os, re, json
from pathlib import Path

BASE = Path(__file__).resolve().parent
SYMBOLS_PATH = BASE / "symbols.json"          
EXTRA_PATH   = BASE / "symbols_extra.json"    

def load_json(p: Path) -> dict:
    if not p.exists(): return {}
    with p.open(encoding="utf-8") as f:
        return json.load(f)

def save_json(p: Path, data: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize(s: str) -> str:
    return (s or "").strip().lower()

def extract_abbr(title: str):
    """영상 제목에서 뜨개 약어 자동 추출"""
    title = title.lower()
    abbrs = set()

    # 주요 약어 패턴
    patterns = [
        r"\bk\d+tog\b", r"\bp\d+tog\b", r"\bssk\b", r"\bssp\b",
        r"\bm1l\b", r"\bm1r\b", r"\bm1\b", r"\binc\b", r"\bdec\b",
        r"\bktbl\b", r"\bptbl\b", r"\btbl\b",
        r"\bco\b", r"\bbo\b",
        r"\byo\b", r"\byarn over\b",
        r"\brc\b", r"\blc\b",
        r"\brib\b", r"\b1x1\b", r"\b2x2\b",
        r"\bst-?st\b", r"\bgarter\b", r"\bmoss\b",
        r"\bpm\b", r"\bsm\b", r"\bwyif\b", r"\bwyib\b",
    ]

    for pat in patterns:
        for m in re.findall(pat, title):
            abbrs.add(m.strip())

    return sorted(list(abbrs))

def fetch_videos(url):
    """yt-dlp로 재생목록 내 영상들 불러오기"""
    try:
        import yt_dlp
    except Exception:
        print("❌ yt-dlp 설치 필요: pip install yt-dlp")
        sys.exit(1)

    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries", [])
    videos = []
    for e in entries:
        title = e.get("title") or ""
        link = e.get("url") or ""
        if not link.startswith("http"):
            link = f"https://www.youtube.com/watch?v={link}"
        videos.append({"title": title, "url": link})
    return videos

def main():
    if len(sys.argv) < 2:
        print("사용법: python lib/ingest_youtube_auto.py <YouTube Playlist URL>")
        sys.exit(1)

    url = sys.argv[1]
    base = load_json(SYMBOLS_PATH) or {}
    extra = load_json(EXTRA_PATH) or {}

    # 기존 약어/별칭 목록 수집 (중복 방지)
    known = set()
    for lib in (base, extra):
        for k, v in lib.items():
            known.add(normalize(k))
            for a in v.get("aliases", []):
                known.add(normalize(a))

    videos = fetch_videos(url)
    if not videos:
        print("❌ 재생목록 비어 있음.")
        return

    added = 0
    for v in videos:
        title = v["title"]
        link  = v["url"]
        abbrs = extract_abbr(title)

        if not abbrs:
            continue  # 약어 없는 영상은 스킵

        for ab in abbrs:
            if ab in known:
                continue

            key = ab.upper()
            entry = {
                "name_en": key,
                "name_ko": title,  # 영상 제목 그대로 기록 (추후 수정 가능)
                "desc_ko": "",
                "aliases": [key, title],
                "delta": 0,
                "videos": [{"title": title, "url": link}]
            }
            extra[key] = entry
            known.add(normalize(key))
            added += 1

    save_json(EXTRA_PATH, extra)
    print(f"✅ 새 약어 {added}개 추가 완료 → {EXTRA_PATH}")

if __name__ == "__main__":
    main()