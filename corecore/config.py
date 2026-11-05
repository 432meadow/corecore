"""Paths and tunables. Everything can be overridden with environment variables."""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(os.environ.get("CORECORE_ROOT", Path(__file__).resolve().parent.parent))
MEDIA_DIR = Path(os.environ.get("CORECORE_MEDIA", ROOT / "media"))
DB_PATH = Path(os.environ.get("CORECORE_DB", MEDIA_DIR / "corecore.sqlite3"))
WEB_DIR = ROOT / "web"

SOURCES_DIR = MEDIA_DIR / "sources"    # downloaded originals (removed after clipping unless KEEP_SOURCES)
SEGMENTS_DIR = MEDIA_DIR / "segments"  # the clip pool the player streams from
THUMBS_DIR = MEDIA_DIR / "thumbs"
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


# Titles containing any of these are dropped by the search providers (adult material, gore, tabloid
# violence). Extend with CORECORE_BLOCKLIST="word,word"; set CORECORE_BLOCKLIST=off to disable.
_DEFAULT_BLOCKLIST = [
    "naked", "nude", "nudes", "sex", "sexy", "porn", "xxx", "onlyfans", "ahegao", "sissy", "panties", "lingerie",
    "try on", "try-on", "egirl", "e-girl", "omegle", "strip", "stripper", "hentai", "nsfw", "fetish", "bikini",
    "shooting", "shoots", "shootout", "shot dead", "killed", "killing", "kills", "murder", "homicide", "assassin",
    "beheading", "execution", "gore", "dead body", "suicide", "rape", "isis", "massacre", "snuff", "combat footage",
    "airstrike", "drone strike", "graphic", "terror", "terrorist", "terrorists", "war", "warzone", "frontline",
    "front-line", "combat", "attack", "attacks", "soldier", "soldiers", "military", "army", "troops", "missile",
    "missiles", "invasion", "genocide", "bodies", "9/11", "9 11", "hostage", "hostages", "stabbing", "stabbed",
    "bodycam", "body cam", "police chase", "arrest", "arrested",
    # not footage of the world: cartoons, anime and manga dubs, news and politics, punditry, product reviews,
    # trailers, lectures. Title search on a two-million-video mirror matches these for nearly any innocent
    # word ("paid for" found campaign news, "fog" found the evening news, "blossom" found product reviews),
    # so they are dropped wherever a title or an uploader name carries them. Game clips are not here: they
    # are a theme of the contemporary set; the beauty queries exclude them themselves.
    "gacha", "vtuber", "mmd", "manga", "anime", "dub", "dubbed", "cartoon", "south park", "family guy", "simpsons",
    "news", "newsflash", "newsreel", "skynews", "sky news", "star fox", "breaking", "politics", "political", "election", "campaign", "senator", "congress",
    "governor", "president", "trump", "biden", "clinton", "obama", "dnc", "gop", "maga", "lobbyists",
    "dossier", "fbi", "cia", "bomb", "protest", "protesters", "rally", "riot", "riots", "gaza", "hamas",
    "hezbollah", "idf", "israel", "israeli", "palestine", "palestinian", "zionist",
    "podcast", "interview", "explained", "lecture", "tutorial", "how to", "review", "reviews", "unboxing",
    "product", "haul", "sponsored", "giveaway", "satisfyer", "trailer", "featurette", "recap", "recaps",
    "bloopers", "reaction", "reacts",
    # and what the second beauty scrape let through: memes and sketches, 3D renders and cosplay, crash
    # investigations, air shows of the military, political posts, animal mating
    "meme", "memes", "comedy", "cosplay", "3d", "noob", "black box", "raf", "air force", "navy", "c17", "c-17",
    "fighter jet", "djt", "thehill", "coitus",
    # violence, against animals or people, and the politics that came with the caught-on-camera clips
    "violence", "violent", "brutal", "beaten", "beating", "beat up", "beats up", "beat him", "stomp", "stomps",
    "stomped", "stomping", "punch", "punched", "punches", "punching", "slap", "slapped", "slaps", "rioters",
    "died suddenly", "republican", "republicans", "democrat", "democrats", "j6",
]
_env_block = os.environ.get("CORECORE_BLOCKLIST", "")
BLOCKLIST: list[str] = [] if _env_block.strip().lower() == "off" else (
    _DEFAULT_BLOCKLIST + [w.strip().lower() for w in _env_block.split(",") if w.strip()])

# Footage of Hitler, the Nazis, fascism and the world wars is not part of this piece in any form. These words
# are always on (CORECORE_BLOCKLIST=off does not lift them), and they are matched not only in titles and
# uploader names but in a source's description and subjects on the archive, so a compilation that does not
# name him in its title is caught too; `python -m corecore audit` removes what an older scrape let in.
HARD_BLOCKLIST: list[str] = [
    "hitler", "hitlers", "adolf", "nazi", "nazis", "nazism", "neo-nazi", "neonazi", "third reich", "reich",
    "reichstag", "swastika", "swastikas", "fuhrer", "führer", "fuehrer", "goebbels", "himmler", "goering", "göring",
    "heydrich", "eichmann", "mengele", "rommel", "wehrmacht", "luftwaffe", "kriegsmarine", "gestapo", "waffen-ss",
    "waffen ss", "hitler youth", "hitlerjugend", "nuremberg rally", "nuremberg trials", "triumph of the will",
    "triumph des willens", "riefenstahl", "wochenschau", "kristallnacht", "holocaust", "shoah", "auschwitz",
    "concentration camp", "death camp", "mussolini", "fascist", "fascists", "fascism", "ww2", "wwii", "ww ii",
    "world war 2", "world war ii", "second world war", "ww1", "wwi", "world war 1", "world war i", "first world war",
    "blitz", "blitzkrieg", "d-day", "propaganda",
    # and cruelty, to animals above all: never in the piece, whatever the title says
    "animal abuse", "animal cruelty", "cruelty", "abuse", "abused", "abusing", "abuser", "brutality", "brutalized",
    "torture", "tortured", "torturing", "maltreatment", "mistreated", "mistreatment", "beaten to death",
    "beat him to death", "beat her to death",
]

# Accounts whose posts are campaigns, lobbying or activism rather than footage of the world; matched against
# the uploader name, case-insensitively. Extend with CORECORE_BLOCKED_UPLOADERS="name,name"; "off" disables.
_DEFAULT_BLOCKED_UPLOADERS = [
    "officialpeta", "israelinusa", "aipac", "btselem", "govchristie", "roosterteeth",
    # accounts behind the caught-on-camera clips: an animal kicked in the street, a man beaten to death,
    # "died suddenly" deaths, campaign and partisan posts, true crime, tabloids
    "ray garcia", "diedsuddenly", "the lincoln project", "theblaze", "newsmax", "heartland signal", "andy ngô",
    "andy ngo", "disclose tv", "t greg doucette", "the sun", "investigation discovery", "the intercept",
    "mumeixxx",
]


def _norm_uploader(name: str | None) -> str:
    """An uploader name as letters and digits only, so that "Ray Garcia 🇺🇸" matches "ray garcia"."""
    return " ".join("".join(ch if ch.isalnum() else " " for ch in (name or "").lower()).split())


_env_up = os.environ.get("CORECORE_BLOCKED_UPLOADERS", "")
BLOCKED_UPLOADERS: set[str] = set() if _env_up.strip().lower() == "off" else (
    {_norm_uploader(u) for u in _DEFAULT_BLOCKED_UPLOADERS} | {_norm_uploader(u) for u in _env_up.split(",") if u.strip()})

# Sources removed by hand after someone saw them, as "provider:external_id": the audit bans their clips and
# deletes the files, and the archive search never offers them again.
BANNED_SOURCES: set[str] = {
    "archive:twitter-1295991588083163136",   # a raccoon kicked in the street at night
    "archive:TikTok-7130942596586818818",    # a clip that frames its subject as a schoolchild, sexually
}


_BLOCK_RE = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(w) for w in BLOCKLIST) + r")(?![a-z0-9])") if BLOCKLIST else None
_HARD_RE = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(w) for w in HARD_BLOCKLIST) + r")(?![a-z0-9])")


def hard_blocked(text: str | None) -> bool:
    """True when any text about a source (title, uploader, description, subjects) names Hitler, the Nazis, fascism
    or the world wars. Whole words, case-insensitive."""
    return bool(_HARD_RE.search((text or "").lower()))


def blocked_title(title: str | None) -> bool:
    """Whole-word match (so "war" does not catch "warm" or "software"), case-insensitive."""
    if hard_blocked(title):
        return True
    if not _BLOCK_RE:
        return False
    return bool(_BLOCK_RE.search((title or "").lower()))


def blocked_source(title: str | None, uploader: str | None = None) -> bool:
    """A source is dropped when its title carries a blocked word, when its uploader name does (a channel called
    "... News"), or when the uploader is on the blocked-accounts list."""
    up = _norm_uploader(uploader)
    return blocked_title(title) or (bool(up) and (up in BLOCKED_UPLOADERS or blocked_title(uploader)))


def ensure_dirs() -> None:
    for d in (MEDIA_DIR, SOURCES_DIR, SEGMENTS_DIR, THUMBS_DIR, INBOX_DIR):
        d.mkdir(parents=True, exist_ok=True)
