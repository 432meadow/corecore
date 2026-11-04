# corecore

An endless found-footage montage in the corecore aesthetic. A Python backend scrapes video (Internet
Archive, anything yt-dlp can reach, or your own files), chops it into shots, and the browser edits those
shots into an infinite stream: slow sad set-up, accelerating cuts, a burst of blisteringly fast ones, a
held image, a cut to black. Over and over, never the same twice, reproducible by seed.

What the genre is and which of its conventions the generator encodes: [docs/CORECORE.md](docs/CORECORE.md).
Where this is going next: [docs/ROADMAP.md](docs/ROADMAP.md).

## Quick start

Requirements: Python 3.11+, ffmpeg and ffprobe on your PATH, a modern browser (Chrome, Edge, Firefox,
Safari 17+).

```bash
pip install -r requirements.txt
python -m corecore serve
```

Open http://127.0.0.1:8000 and press start. The pool is empty at first, so open the controls (`h`) and
either queue the starter set (Internet Archive, public domain and Creative Commons material) or run a
scrape of your own. Clips appear in the stream as soon as the worker has cut them.

The same thing from a terminal:

```bash
python -m corecore seed
```

```bash
python -m corecore ingest --provider archive --query "collection:prelinger AND subject:(suburbs)" --max 5 --tags archive,home
```

```bash
python -m corecore ingest --provider local --url ~/Videos/holiday --tags home,childhood
```

Drop music into `media/music/` (mp3, ogg, wav, m4a, flac) and it shows up in the music menu, with an
optional slowed + reverb treatment. With no music of your own, a built-in generative ambient bed plays.

## How it works

```
providers (archive | ytdlp | local)
   └─ download ──► ffmpeg shot detection ──► 1.2–8 s clips at 720p (h264/aac, faststart)
                                               └─ thumbnail, brightness / saturation / motion / loudness
                                                  └─ SQLite catalogue (media/corecore.sqlite3)
                                                        │  /api/clips/sample  (seeded random window)
                                                        ▼
browser: catalog.js ──► sequencer.js (phrases + modes) ──► player.js (8 preloaded <video>s, canvas compositor)
                                   ▲                             │
                             audio.js: music, ducking, onsets, generative bed, recording bus
```

- **Backend** (`corecore/`): FastAPI app, a SQLite job queue drained by one worker thread, three
  providers, and ffmpeg wrappers. Nothing beyond ffmpeg is needed at runtime; there is no ML yet.
- **Sequencer** (`web/sequencer.js`): a seeded random walk through phrases (`dwell`, `voice`,
  `juxtapose`, `build`, `burst`, `climax`, `black`). Each cycle picks a contrast pair of tags, one or two
  motif clips that come back, and durations/speeds/treatments from the current mode's parameters.
- **Player** (`web/player.js`): cuts on the AudioContext clock, cover-fits clips with a slow push-in,
  adds grain, vignette, flashes, letterboxing, shake, double exposure, freeze frames and captions, and
  lets strong music onsets pull a cut forward.
- **Modes**: `corecore` (default), `hopecore` (warmer, quotes, no cut to black), `chaos` (the 2023
  nichetok turn: layered, random speeds), `dwell` (long takes only).

## Controls

| key | action |
| --- | --- |
| space | pause / resume |
| n | skip to the next phrase |
| . | skip this cut |
| h | show / hide the controls |
| i | debug overlay (phrase, clip, tags, queue, onsets) |
| f | fullscreen |
| r | start / stop recording (downloads a WebM of what you saw and heard) |
| s | new seed |
| m | next mode |
| v | toggle 16:9 / 9:16 |
| x | ban the current clip (removed from the pool for good) |

The URL carries `seed`, `mode`, `aspect`, `music` and `slowed`, so a link reproduces a stream over the same
pool. "copy link" in the controls does that for you.

## Sources, and a note on what you may scrape

- **Internet Archive** (`archive`): the default. Public-domain and Creative-Commons video; the
  Prelinger ephemeral films, NASA, newsreels, community uploads. Queries use the archive's search syntax,
  e.g. `collection:prelinger AND subject:(television commercials)`, or paste an item URL. The `license`
  field is stored per source.
- **yt-dlp** (`ytdlp`): YouTube search terms, or any video/playlist/channel URL yt-dlp supports (Vimeo,
  Dailymotion, TikTok, archive.org...). Downloading from YouTube is against its terms of service, and
  YouTube blocks most anonymous datacenter traffic; from a home connection set
  `YTDLP_COOKIES_FROM_BROWSER=chrome` (or `YTDLP_COOKIES_FILE=cookies.txt`). Keep the result for personal
  use; a public deployment built on scraped commercial footage is your call and your risk.
- **local** (`local`): files in `media/inbox/`, or any directory, file or glob you point it at. Originals
  are never deleted.

Sources that fail (no mp4 derivative, too long, download error) are recorded with the error in `/api/sources`
and skipped; the job carries on.

## Configuration

Environment variables, all optional:

| variable | default | meaning |
| --- | --- | --- |
| `CORECORE_MEDIA` | `./media` | where clips, thumbnails, music and the database live |
| `CORECORE_SEGMENT_HEIGHT` | 720 | clip height; width follows the source aspect |
| `CORECORE_SEGMENT_FORMAT` | mp4 | `mp4` (h264/aac) or `webm` (vp9/opus) |
| `CORECORE_MIN_SHOT` / `CORECORE_MAX_SHOT` | 1.2 / 8.0 | shot length bounds in seconds; longer shots are carved into chunks |
| `CORECORE_MAX_CLIPS_PER_SOURCE` | 24 | spread evenly through the source |
| `CORECORE_SCENE_THRESHOLD` | 0.30 | ffmpeg scene-change score; lower finds more cuts |
| `CORECORE_MAX_SOURCE_DURATION` | 1800 | skip sources longer than this (seconds) |
| `CORECORE_MAX_SOURCE_BYTES` | 600 MB | skip or abort larger downloads |
| `CORECORE_KEEP_SOURCES` | 0 | keep downloaded originals in `media/sources/` |
| `CORECORE_NO_WORKER` | unset | `1` disables the in-process worker (run `python -m corecore worker` elsewhere) |
| `YTDLP_COOKIES_FROM_BROWSER`, `YTDLP_COOKIES_FILE`, `YTDLP_MAX_HEIGHT` | | yt-dlp options |

## API

| method and path | what |
| --- | --- |
| `GET /api/stats` | clip, source and tag counts |
| `GET /api/clips/sample?n=&seed=&tags=&exclude=` | random window of playable clips (seeded order) |
| `GET /api/clips?offset=&limit=&tag=` | browse newest first |
| `POST /api/clips/{id}/ban` (`?undo=1`) | remove from / restore to the pool |
| `GET /api/sources` | ingested sources with status, license and clip counts |
| `GET /api/jobs`, `POST /api/jobs`, `POST /api/jobs/{id}/cancel` | the ingest queue |
| `POST /api/seed` | queue the starter Internet Archive jobs |
| `GET /api/music` | tracks in `media/music/` |
| `GET /media/...` | clips, thumbnails, music (range requests supported) |

## Tests

```bash
python -m unittest discover -s tests -v
```

Pure-function tests plus a short ffmpeg round trip on synthetic footage. The providers that need the
network are exercised against fixtures only.

## Layout

```
corecore/            backend package (config, db, ffmpeg, ingest, jobs, app, providers/, seeds, CLI)
web/                 the player: index.html, app.js, player.js, sequencer.js, audio.js, catalog.js, prng.js, recorder.js
docs/                CORECORE.md (research + rules), ROADMAP.md
tests/               unit tests
media/               created at runtime: segments/, thumbs/, music/, inbox/, sources/, corecore.sqlite3 (git-ignored)
```
