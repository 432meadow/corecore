# corecore

An endless found-footage montage in the corecore aesthetic. A Python backend scrapes video (Internet
Archive, anything yt-dlp can reach, or your own files), chops it into shots, and the browser edits those
shots into an infinite stream: slow sad set-up, accelerating cuts, a burst of blisteringly fast ones, a
held image, a cut to black. Over and over, never the same twice, reproducible by seed.

**Watch it:** https://432meadow.github.io/corecore/ is the static edition, rebuilt weekly by CI from
public-domain footage on the Internet Archive. Add `?seed=live` and you are on the live channel: everyone
on that URL sees the same edit at the same moment.

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

## Two editions

| | full app | static edition (GitHub Pages) |
| --- | --- | --- |
| runs | `python -m corecore serve` on your machine | any static host; CI builds it |
| footage | whatever you scrape or drop in, unlimited | a bounded slice of the pool (default 450 MB) exported with `python -m corecore export` |
| scraping | from the browser or the CLI, any provider | done by the GitHub Actions workflow from the Internet Archive, cached between runs so the pool grows |
| music | your tracks in `media/music/` + generated bed | generated bed (+ any tracks exported with the site) |
| curation | ban clips for everyone | ban clips for yourself (localStorage) |

The static edition is the same player: `index.html` just carries `window.CORECORE_STATIC = "manifest.json"`
and the catalogue reads the manifest instead of the API. `.github/workflows/pages.yml` does the rest:
scrape within a time budget, clip, export, deploy. Trigger it by hand from the Actions tab (inputs: time
budget and size budget), or let the Monday schedule run.

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
- **Found text**: captions are drawn half the time from the source's own title ("a date with your
  family", "design for dreaming"), the rest from a small built-in pool or your own lines.
- **Faces**: with `opencv-python-headless<5` installed, clips get a `faces` tag from a Haar cascade run
  on three frames, and the sequencer prefers them for motifs and climaxes.
- **Live channel** (`?seed=live`, key `l`): the seed is derived from the clock in 10-minute windows and a
  joining viewer fast-forwards through the deterministic cue stream to the current position. Beat
  snapping is off in this mode so every viewer's cuts stay aligned (within a cut or two; stalls resync at
  the next window).

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
| l | live channel |
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

## Deploying

- **GitHub Pages**: push to `main` (or run the `pages` workflow). One-time setup in the repository
  settings: Pages → Source → "GitHub Actions". The workflow needs the repository to be public, or a
  plan that allows private Pages.
- **Full app in Docker**: `docker build -t corecore . && docker run -p 8000:8000 -v corecore-media:/app/media corecore`.
  Put a reverse proxy with auth in front before exposing the ingest form to the internet: the local
  provider reads paths on the server and yt-dlp fetches whatever URL it is given.
- **Static export anywhere**: `python -m corecore export --out site --max-mb 450` and upload `site/`.

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
| `CORECORE_ARCHIVE_PREFER_SMALL` | 0 | `1` prefers the 512 kb/s Internet Archive derivative (faster builds) |
| `CORECORE_ARCHIVE_PAGE` | 1 | which page of Internet Archive results to take (CI rotates it weekly) |
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

Pure-function tests, the exporter, the CI budget runner and a short ffmpeg round trip on synthetic footage.
The providers that need the network are exercised against fixtures only; the real test of the Internet
Archive provider is the `pages` workflow log.

## Layout

```
corecore/            backend package (config, db, ffmpeg, ingest, faces, export, jobs, app, providers/, seeds, CLI)
web/                 the player: index.html, app.js, player.js, sequencer.js, audio.js, catalog.js, prng.js, recorder.js
.github/workflows/   pages.yml (scrape + export + deploy), tests.yml
docs/                CORECORE.md (research + rules), ROADMAP.md
tests/               unit tests
media/               created at runtime: segments/, thumbs/, music/, inbox/, sources/, corecore.sqlite3 (git-ignored)
site/                output of `export` / `build-site` (git-ignored)
```
