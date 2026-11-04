"""Paths and tunables. Everything can be overridden with environment variables."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("CORECORE_ROOT", Path(__file__).resolve().parent.parent))
MEDIA_DIR = Path(os.environ.get("CORECORE_MEDIA", ROOT / "media"))
DB_PATH = Path(os.environ.get("CORECORE_DB", MEDIA_DIR / "corecore.sqlite3"))
WEB_DIR = ROOT / "web"

SOURCES_DIR = MEDIA_DIR / "sources"    # downloaded originals (removed after clipping unless KEEP_SOURCES)
SEGMENTS_DIR = MEDIA_DIR / "segments"  # the clip pool the player streams from
THUMBS_DIR = MEDIA_DIR / "thumbs"
MUSIC_DIR = MEDIA_DIR / "music"        # drop your own tracks here (mp3/ogg/wav/m4a/flac)
INBOX_DIR = MEDIA_DIR / "inbox"        # drop your own footage here and run the `local` provider

# Clipping
SEGMENT_HEIGHT = int(os.environ.get("CORECORE_SEGMENT_HEIGHT", 720))
SEGMENT_FORMAT = os.environ.get("CORECORE_SEGMENT_FORMAT", "mp4")  # "mp4" (h264/aac) or "webm" (vp9/opus)
MIN_SHOT = float(os.environ.get("CORECORE_MIN_SHOT", 1.2))        # seconds; shorter shots are discarded
MAX_SHOT = float(os.environ.get("CORECORE_MAX_SHOT", 8.0))        # seconds; longer shots are carved into chunks
MAX_CHUNKS_PER_SHOT = int(os.environ.get("CORECORE_MAX_CHUNKS_PER_SHOT", 4))
MAX_CLIPS_PER_SOURCE = int(os.environ.get("CORECORE_MAX_CLIPS_PER_SOURCE", 24))
SCENE_THRESHOLD = float(os.environ.get("CORECORE_SCENE_THRESHOLD", 0.30))  # ffmpeg scene score 0..1
ANALYSIS_WIDTH = int(os.environ.get("CORECORE_ANALYSIS_WIDTH", 320))

# Sources
MAX_SOURCE_DURATION = float(os.environ.get("CORECORE_MAX_SOURCE_DURATION", 30 * 60))  # seconds
MAX_SOURCE_BYTES = int(os.environ.get("CORECORE_MAX_SOURCE_BYTES", 600 * 1024 * 1024))
KEEP_SOURCES = os.environ.get("CORECORE_KEEP_SOURCES", "0") == "1"
HTTP_USER_AGENT = os.environ.get("CORECORE_USER_AGENT", "corecore/0.1 (+https://github.com/)")

FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")

# yt-dlp: YouTube increasingly refuses anonymous datacenter traffic; point at a cookies file or browser profile.
YTDLP_COOKIES_FILE = os.environ.get("YTDLP_COOKIES_FILE")
YTDLP_COOKIES_FROM_BROWSER = os.environ.get("YTDLP_COOKIES_FROM_BROWSER")  # e.g. "chrome", "firefox"
YTDLP_MAX_HEIGHT = int(os.environ.get("YTDLP_MAX_HEIGHT", 720))

VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".mpg", ".mpeg", ".m2ts", ".flv", ".wmv", ".ogv"}

# Directories the `local` provider may read when a job comes in over the API. The CLI adds the path you give it.
LOCAL_ROOTS: list[Path] = [INBOX_DIR] + [Path(p).expanduser() for p in os.environ.get("CORECORE_LOCAL_ROOTS", "").split(os.pathsep) if p]
MUSIC_EXTENSIONS = {".mp3", ".ogg", ".oga", ".wav", ".m4a", ".flac", ".aac", ".opus"}


# Titles containing any of these are dropped by the search providers (adult material, gore, tabloid
# violence). Extend with CORECORE_BLOCKLIST="word,word"; set CORECORE_BLOCKLIST=off to disable.
_DEFAULT_BLOCKLIST = [
    "naked", "nude", "nudes", "sex", "sexy", "porn", "xxx", "onlyfans", "ahegao", "sissy", "panties", "lingerie",
    "try on", "try-on", "egirl", "e-girl", "omegle", "strip", "stripper", "hentai", "nsfw", "fetish", "bikini",
    "shooting", "shoots", "shootout", "shot dead", "killed", "killing", "kills", "murder", "homicide", "assassin",
    "beheading", "execution", "gore", "dead body", "suicide", "rape", "isis", "massacre", "snuff", "combat footage",
    "airstrike", "drone strike",
]
_env_block = os.environ.get("CORECORE_BLOCKLIST", "")
BLOCKLIST: list[str] = [] if _env_block.strip().lower() == "off" else (
    _DEFAULT_BLOCKLIST + [w.strip().lower() for w in _env_block.split(",") if w.strip()])


def blocked_title(title: str | None) -> bool:
    t = (title or "").lower()
    return any(w in t for w in BLOCKLIST)


def ensure_dirs() -> None:
    for d in (MEDIA_DIR, SOURCES_DIR, SEGMENTS_DIR, THUMBS_DIR, MUSIC_DIR, INBOX_DIR):
        d.mkdir(parents=True, exist_ok=True)
