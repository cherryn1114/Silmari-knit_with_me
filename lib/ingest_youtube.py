# lib/ingest_youtube.py
# 사용법:
#   python lib/ingest_youtube.py <YouTube URL...>
# 예:
#   python lib/ingest_youtube.py "https://youtube.com/playlist?list=PLexrkqgKCXvC5P6B5Zggyz44M6kAU10P1"

import sys, re, json
from pathlib import Path
from typing import Dict, Any, List

BASE = Path(__file__).resolve().parent
SYMBOLS_PATH = BASE / "symbols.json"          # 기존 사전
EXTRA_PATH   = BASE / "symbols_extra.json"    # 새 항목 누적 저장

# -------------------------- JSON 유틸 --------------------------

def _read_json_safely(path: Path) -> Dict[str, Any]:
    """파일이 없거나 비었거나 깨졌으면 {} 반환"""
    if not path.exists():
        return {}
    try:
        txt = path.read_text(encoding="utf-8").strip()
        if not txt:
            return {}
        return json.loads(txt)
    except Exception:
        return {}

def _write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    """임시 파일로 쓴 뒤 교체 (중간 실패 시 0바이트 방지)"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def _normalize(s: str) -> str:
    return (s or "").strip().lower()

# -------------------------- YouTube 수집 --------------------------

def _fetch_entries(urls: List[str]) -> List[Dict[str, Any]]:
    """
    재생목록/단일영상 혼합 URL 리스트 -> [{title, url, lower, has_ko}, ...]
    """
    try:
        import yt_dlp  # pip install yt-dlp
    except Exception:
        print("❌ yt-dlp가 설치되어 있지 않습니다.  `pip install yt-dlp` 실행 후 다시 시도하세요.")
        sys.exit(1)

    out: List[Dict[str, Any]] = []
    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for raw in urls:
            try:
                info = ydl.extract_info(raw, download=False)
            except Exception as ex:
                print(f"⚠️ URL 읽기 실패: {raw}\n   {ex}")
                continue

            if not info:
                continue

            entries = info.get("entries") if isinstance(info, dict) and "entries" in info else [info]
            for e in entries or []:
                title = (e.get("title") or "").strip()
                if not title:
                    continue
                url = (e.get("webpage_url") or e.get("url") or "").strip()
                # 일부는 video id만 들어옴 → 정규화
                if url and not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={url}"
                if not url:
                    continue

                # Shorts 등도 허용하되, "playlist 전용 링크(list=... 만 있고 watch?v= 없음)"는 제외
                if "list=" in url and "watch?v=" not in url:
                    # 개별 영상 링크만 요구사항에 맞게 수집
                    continue

                has_ko = bool(re.search(r"[가-힣]", title))
                out.append({"title": title, "url": url, "lower": title.lower(), "has_ko": has_ko})

    # 링크 기준 중복 제거
    uniq = {}
    for v in out:
        uniq[v["url"]] = v
    return list(uniq.values())

# -------------------------- 메인 로직 --------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: python lib/ingest_youtube.py <YouTube URL...>")
        sys.exit(1)

    urls = sys.argv[1:]

    # 기존/추가 사전 안전 로드
    base  = _read_json_safely(SYMBOLS_PATH) or {}
    extra = _read_json_safely(EXTRA_PATH) or {}

    # 이미 존재하는 키/별칭/이름 인덱스 구성(중복 방지)
    known = set()
    def _index(lib: Dict[str, Any]) -> None:
        for k, v in lib.items():
            known.add(_normalize(k))
            for a in v.get("aliases", []):
                known.add(_normalize(a))
            known.add(_normalize(v.get("name_en", "")))
            known.add(_normalize(v.get("name_ko", "")))

    _index(base)
    _index(extra)

    videos = _fetch_entries(urls)
    if not videos:
        print("비디오를 찾지 못했습니다. URL을 확인하세요.")
        sys.exit(0)

    added = 0
    for v in videos:
        title = v["title"]
        url   = v["url"]
        tnorm = _normalize(title)

        # 제목이 이미 알려진 키/별칭/이름에 포함되면 스킵
        if tnorm in known:
            continue

        # 키 충돌 방지: 같은 제목이 base/extra 키로 이미 존재하면 접미 번호 부여
        key = title
        if key in base or key in extra:
            suffix = 1
            while f"{title} [{suffix}]" in base or f"{title} [{suffix}]" in extra:
                suffix += 1
            key = f"{title} [{suffix}]"

        # 새 항목 구성
        entry = {
            "name_en": title,            # 채널 언어가 한글이어도 우선 name_en에 타이틀을 기록
            "name_ko": title,
            "desc_ko": "",               # 설명은 이후 앱에서 보강 가능
            "aliases": [title],
            "delta": 0,                  # 증감 정보 알 수 없으므로 0
            "videos": [{"title": title, "url": url}],  # 요구사항: 개별 영상 1개
        }

        extra[key] = entry
        # 중복 방지 인덱스에 반영
        known.add(tnorm)
        known.add(_normalize(key))
        added += 1

    # 원자적 저장
    _write_json_atomic(EXTRA_PATH, extra)

    print(f"✅ 새로 추가된 항목: {added}개")
    print(f"📝 저장: {EXTRA_PATH}")

if __name__ == "__main__":
    main()