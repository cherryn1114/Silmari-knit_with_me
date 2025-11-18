import re

def get_youtube_thumbnail(url: str) -> str:
    patterns = [
        r"youtu\.be/([A-Za-z0-9_-]+)",
        r"youtube\.com/watch\?v=([A-Za-z0-9_-]+)",
        r"youtube\.com/embed/([A-Za-z0-9_-]+)",
        r"youtube\.com/v/([A-Za-z0-9_-]+)"
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            video_id = m.group(1)
            return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    return None