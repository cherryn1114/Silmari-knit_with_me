# lib/utils.py
import re
from urllib.parse import urlparse, parse_qs

def get_youtube_thumbnail(url: str) -> str:
    """
    유튜브 '영상' URL에서 썸네일 이미지 URL 반환.
    - https://youtu.be/VIDEO_ID?si=...
    - https://www.youtube.com/watch?v=VIDEO_ID&...
    - https://www.youtube.com/shorts/VIDEO_ID?...
    - https://www.youtube.com/embed/VIDEO_ID
    등 웬만한 형태를 다 처리.
    실패하면 ""(빈 문자열) 반환.
    """
    if not url:
        return ""

    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception:
        return ""

    host = (parsed.netloc or "").lower()
    path = parsed.path or ""
    qs   = parse_qs(parsed.query or "")

    video_id = ""

    # 1) youtu.be 단축 링크: https://youtu.be/VIDEO_ID?...
    if "youtu.be" in host:
        # /VIDEO_ID 형태
        video_id = path.lstrip("/").split("/")[0]

    # 2) 일반 youtube.com 링크
    if (not video_id) and "youtube.com" in host:
        # watch?v=VIDEO_ID
        if "v" in qs and qs["v"]:
            video_id = qs["v"][0]
        # /shorts/VIDEO_ID
        elif "/shorts/" in path:
            video_id = path.split("/shorts/")[1].split("/")[0]
        # /embed/VIDEO_ID
        elif "/embed/" in path:
            video_id = path.split("/embed/")[1].split("/")[0]
        # /live/VIDEO_ID
        elif "/live/" in path:
            video_id = path.split("/live/")[1].split("/")[0]

    # 3) 그래도 못 찾으면 마지막 백업: URL 전체에서 ID처럼 생긴 부분 찾기
    if not video_id:
        m = re.search(r"([A-Za-z0-9_-]{6,})", url)
        if m:
            video_id = m.group(1)

    if not video_id:
        return ""

    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"