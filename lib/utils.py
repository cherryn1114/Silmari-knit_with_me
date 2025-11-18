# lib/utils.py
import re
from urllib.parse import urlparse, parse_qs

def get_youtube_thumbnail(url: str) -> str:
    """
    유튜브 '영상' URL에서 썸네일 이미지 URL을 만들어 반환.
    - youtu.be/VIDEO_ID
    - youtube.com/watch?v=VIDEO_ID&...
    - youtube.com/embed/VIDEO_ID
    처럼 웬만한 형태는 다 잡아줌.
    못 찾으면 빈 문자열("") 반환.
    """
    if not url:
        return ""

    url = url.strip()

    # 1) 전체 URL 파싱
    try:
        parsed = urlparse(url)
    except Exception:
        return ""

    host = (parsed.netloc or "").lower()
    path = parsed.path or ""
    qs   = parse_qs(parsed.query or "")

    video_id = ""

    # 2) youtu.be 단축 링크: https://youtu.be/VIDEO_ID?si=...
    if "youtu.be" in host:
        # /VIDEO_ID 형태
        video_id = path.lstrip("/").split("/")[0]

    # 3) 일반 watch 링크: https://www.youtube.com/watch?v=VIDEO_ID&...
    if (not video_id) and "youtube.com" in host:
        if "v" in qs and qs["v"]:
            video_id = qs["v"][0]
        # /embed/VIDEO_ID 형태 지원
        elif "/embed/" in path:
            video_id = path.split("/embed/")[1].split("/")[0]
        # /v/VIDEO_ID 형태
        elif "/v/" in path:
            video_id = path.split("/v/")[1].split("/")[0]

    # 4) 그래도 못 찾으면 정규식 백업
    if not video_id:
        m = re.search(r"([A-Za-z0-9_-]{6,})", url)
        if m:
            video_id = m.group(1)

    if not video_id:
        return ""

    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
