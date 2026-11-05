# corecore

On the page it is called *absolute clarity*. An endless found-footage montage in the corecore aesthetic. A Python backend scrapes video (Internet
Archive, anything yt-dlp can reach, or your own files), chops it into shots, and the browser edits those
shots into an infinite stream: slow sad set-up, accelerating cuts, a burst of blisteringly fast ones, a
held image, a cut to black. Over and over, never the same twice, reproducible by seed.

**Watch it:** https://432meadow.github.io/corecore/ is the static edition, rebuilt weekly by CI from
contemporary web video mirrored on the Internet Archive (see Sources). Add `?seed=live` and you are on the live channel: everyone
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

There is no music: the only sound under the footage is the desk (see below), and the footage's own
sound, which surfaces now and then as if heard through a small speaker across the room.

## Two editions

| | full app | static edition (GitHub Pages) |
| --- | --- | --- |
| runs | `python -m corecore serve` on your machine | any static host; CI builds it |
| footage | whatever you scrape or drop in, unlimited | a bounded slice of the pool (default 450 MB) exported with `python -m corecore export` |
| scraping | from the browser or the CLI, any provider | done by the GitHub Actions workflow from the Internet Archive, cached between runs so the pool grows |
| sound | the desk, synthesized in the browser | the same |
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
                             audio.js: clip sound through a speaker, the wash, onsets, the desk, recording bus
```

- **Backend** (`corecore/`): FastAPI app, a SQLite job queue drained by one worker thread, three
  providers, and ffmpeg wrappers. Nothing beyond ffmpeg is needed at runtime; there is no ML yet.
- **Sequencer** (`web/sequencer.js`): a seeded random walk through phrases (`dwell`, `voice`,
  `juxtapose`, `build`, `burst`, `climax`, `black`). Each cycle picks a contrast pair of tags, one or two
  motif clips that come back, and durations/speeds/treatments from the current mode's parameters.
- **Player** (`web/player.js`): cuts on the AudioContext clock, cover-fits clips with a slow push-in,
  adds grain, vignette, flashes, letterboxing, shake, double exposure, freeze frames and captions, and
  lets the desk's mouse clicks pull a cut forward.
- **The desk** (`web/desk.js`): the only sound there is. Instead of music, a room with a computer in it:
  a PC fan with a blade tone that speeds up when the edit gets frantic, mouse clicks and scroll-wheel
  ticks, the mouse sliding, a mug set down now and then, a low room tone; no keyboard. Everything is
  synthesized from noise bursts and sine bodies. The desk is busy through builds and bursts, still at the
  climax, and nearly silent after the cut to black; clicks emit onsets, so cuts can land on them. It is
  never ducked: when the footage's own sound comes in, it plays over the desk. Each mode balances it its
  own way (`hopecore` a lighter hand and the mug more often, `chaos` busy hands, `dwell` mostly the fan).
  There is no music menu: an earlier generative ambient wash was taken out because it took away from the
  piece.
- **Frame and haze**: the picture sits inside the frame, smaller than it, its edges feathered into the
  page; the footage is softened with a slight gaussian blur and then grained, so it reads as something seen
  from a little way off. One fader drives all of it: it loads at its fullest on a computer (`?edge=1`) and
  at 0.40 on a phone, where the screen is small; 0 is full bleed, sharp and clean.
- **The page**: by default the picture sits on an off-white page, like a print, with captions set in ink;
  a cut to black is then a cut to the page, the vignette stays inside the picture and a flash blows out the
  picture alone. `[ dark ]` in the controls puts it back on a black screen, `[ as the system has it ]`
  follows the device; the choice is remembered in the browser.
- **Clip audio through computer speakers**: when the footage's own sound surfaces (voice phrases, jump
  cuts) it arrives one layer removed, as if from a small speaker across the room: no low end, a rolled-off
  top, a cabinet resonance and a boxy dip, a touch of soft clipping, a short bright reflection, a narrowed
  image. Measured at the output: 31 dB down below 120 Hz, +7 dB at 2-3 kHz, 13 dB off above 8 kHz. The
  controls offer a tinnier phone-speaker voicing and the direct sound (`?clipfx=phone|direct`).
- **The wash**: when a clip's sound is cut, it washes away instead of stopping. Its last moment is thrown
  into a long, dark stereo reverb: the dry is muted at the cut, the clip plays on unheard for a fifth of a
  second to feed the reverb, and the tail blooms about 7 dB under the sound and dies away over some 2.5
  seconds. A sound bleeding across a cut dissolves into the same reverb as it fades. Cuts shorter than
  0.6 s (bursts) stay dry, and nothing else in the piece reaches the reverb.
- **Modes**: `corecore` (default), `online` (contemporary material with a cinematic treatment: slow
  motion and speed ramps, vlog jump cuts, sound bleeding across cuts), `hopecore` (warmer,
  quotes, no cut to black), `chaos` (the 2023 nichetok turn: layered, random speeds, textures), `dwell`
  (long takes only).
- **Cinematic treatment**: every cycle picks a colour grade (cold, night, bleach, mono, warm, neutral:
  filter, lifted blacks, tint, highlight bloom), speed ramps slow motion-heavy shots down and catch up
  before the cut, a voice keeps talking under the next shot (L-cut), bursts occasionally stutter a moment
  two or three times, and rare textures (low-res re-upload, chromatic aberration) mark the material as
  something that travelled through the internet. Title cards on black use the sources' own titles.
  Frames: 16:9, 2.39:1 scope, 9:16, 1:1. Clips fill the frame edge to edge, cropped, never letterboxed
  into a band: in 9:16 every clip (a wide one keeps near its middle and drifts slowly across during the
  shot, a tenth of the frame a second, so what it holds passes through), in 16:9 and 1:1 a phone clip
  (keeping its upper middle, where faces are). Only the 2.39:1 frame shows phone footage whole, over a
  soft dark copy of itself, since a fill there would keep a quarter of its height.
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
| v | cycle 16:9, 9:16, 1:1, 2.39:1 |
| x | ban the current clip (removed from the pool for good) |

The URL carries `seed`, `mode`, `tags`, `edge` and `clipfx`, and `aspect` once a frame has been chosen, so
a link reproduces a stream over the same pool; `[ share this stream ]` in the controls copies it.

**Between streams.** A new seed (or the live channel) does not cut: the picture fades out to the page over
half a second and the sound with it, a full second of silence on the empty page, then the new stream fades
in, picture and sound together. A second switch made during the fade takes its place.

**On a phone.** The picture opens in the vertical frame (9:16), with frame and haze at 0.40, and follows the phone as it turns, until a
frame is chosen by hand. A tap on the picture opens and closes the controls, which rise as a sheet over the
lower part of the screen with the picture still in view above; every word in brackets is a 44 px target,
and `[ pause ]` stands in for the space bar. On a computer a click on the picture does the same. The viewer itself carries no text: the
status line (mode · seed · state) and the source of the clip on screen sit at the top of the controls.

**The look.** The controls wear the elsewhere look: Roboto or Helvetica at 16, 14 and 13 px and one
weight, everything lowercase, off-white or near-black with three grays and a warm and a cool accent
(`[ off-white ]`, `[ dark ]` or `[ as the system has it ]` in the controls; off-white is the default). Every act and switch is a word in square
brackets, with no box, border, fill or icon; a button says what it did, or what it is waiting on, in its
own brackets, and a status line at the top of the controls carries mode, seed and state in fields separated
by middle dots. There are no toasts, spinners or sounds from the interface, and no text on the viewer.

## Sources

Three starter sets, one switch (`--set contemporary|beauty|archival|all`, or the buttons in the controls):

- **beauty** (also inside the contemporary set, early in the list): kindness and subtle natural
  poignance, from corners of the archive where the footage is what its title says. The park service's
  own camera work in Yellowstone and Arches (wolves, bison in snow, morning fog, a sunrise), Flickr's
  wildlife, light, water and home clips (herons, owls, fledglings, sunsets, fog, waves, rain on a window,
  sledding, first snow), the wildlife and land agencies' rivers and creatures, nature centres' trail
  cameras, nest boxes and osprey cams, the Brooks Falls bear cam, public pianos, buskers, the 2005-06
  camcorder years of Ourmedia (first steps, birthdays, grandparents), gardens and farms, rain, snowfall,
  lighthouses and lit windows, Grand Canyon b-roll, aquarium tanks. Title searches on the
  YouTube mirror were tried first and found games, manga dubs and news for innocent words, so they are
  gone from this set. Tagged `beauty`, `kind`, `light`, `trailcam`, so the sequencer can cut kindness
  against traffic and beauty against screens; `hopecore` prefers them.
- **contemporary** (the default): internet-native material. The Internet Archive's `mirrortube` collection
  holds about two million YouTube videos that people archived, 920k of them from 2022 on, with H.264 files:
  dashcams, vlogs, walking tours, driving POVs, doorbell and CCTV clips, game moments, pets, raw footage,
  ASMR. The queries use quoted phrases (the archive's search treats `dash cam` as dash OR cam), newest-first
  ordering (`|sort=date desc` on any archive query) and a title blocklist (`CORECORE_BLOCKLIST`) that drops
  adult and gore uploads, which otherwise dominate the popular end of that collection.
- **archival**: the Prelinger ephemeral films, NASA and other public-domain footage. Legally the cleanest
  pool. The public GitHub Pages build scrapes the contemporary set and exports only clips tagged `modern`;
  its `seed_set` workflow input switches it.

Providers:

- **Internet Archive** (`archive`): any search in the archive's own syntax, or an item URL. Works from
  datacenters and CI. Item licences are stored per source.
- **yt-dlp** (`ytdlp`): YouTube search terms, or any URL yt-dlp understands (YouTube, TikTok, Vimeo,
  Twitch clips, Reddit posts...), or a pasted list of links, one per line. YouTube and TikTok block most
  datacenter addresses (HTTP 403 on the video data), so run this provider on your own machine, where it
  works, and with `YTDLP_COOKIES_FROM_BROWSER=chrome` (or `YTDLP_COOKIES_FILE`) it uses your own logged-in
  session. This project does not try to get around those blocks. Downloading from YouTube is against its
  terms of service; keep the result for personal use.
- **Dailymotion** (`dailymotion`): public search API, no key; lots of dashcam compilations and odd uploads.
  Downloads go through yt-dlp, whose Dailymotion extractor needs its browser-impersonation extra
  (`pip install curl_cffi`); without it the job fails with that message.
- **Reddit** (`reddit`): video posts from one or more subreddits (r/dashcam, r/oddlyterrifying,
  r/liminalspace...) or a post URL. Needs a free Reddit "script" app: `REDDIT_CLIENT_ID` and
  `REDDIT_CLIENT_SECRET`. The DASH video and audio tracks are fetched directly and merged with ffmpeg.
  Untested from this side: Reddit refuses unauthenticated datacenter traffic, so it was built against the
  documented API and a fixture.
- **live streams** (`stream`): public HLS/RTSP/RTMP URLs (traffic cameras, harbour cams, city webcams),
  one per line; ffmpeg records `CORECORE_STREAM_SECONDS` (default 90) of each and the slice is clipped like
  any other source. Every recording is a new source, so the same camera can be recorded forever.
- **local** (`local`): files in `media/inbox/`, or, from the CLI, any directory, file or glob. Over the API
  the provider only reads `media/inbox` and `CORECORE_LOCAL_ROOTS`. Originals are never deleted. The simplest
  contemporary workflow: download on your laptop with your own tools, drop the files here.

Also in the contemporary set: the Archive's mirrored short-form uploads (78k TikToks, 11k Instagram reels,
142k Twitter videos, identifiers `tiktok-*`, `instagram-*`, `twitter-*`), whose titles are the original
captions, so hashtag words such as `grwm` or `dayinmylife` work as queries.

A word on publishing: the archival set is public domain. Mirrored web video is other people's work; a
private pool is one thing, a public site built from it is your call and your risk.

## Configuration

Environment variables, all optional:

| variable | default | meaning |
| --- | --- | --- |
| `CORECORE_MEDIA` | `./media` | where clips, thumbnails and the database live |
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
| `CORECORE_BLOCKLIST` | built-in list | extra comma-separated title words to drop; `off` disables the filter. The built-in list covers adult material, violence and war, and off-topic material a title search keeps finding by accident: anime and manga dubs, cartoons, news and politics, punditry, product reviews, trailers, memes and sketches, 3D renders and cosplay |
| `CORECORE_BLOCKED_UPLOADERS` | a short built-in list | extra comma-separated uploader names to drop (accounts that post campaigns, lobbying or activism rather than footage of the world); `off` disables it. A blocklist word in an uploader name, such as "news", also drops the source |
| `CORECORE_LOCAL_ROOTS` | `media/inbox` | extra directories the local provider may read over the API (path-separator separated) |
| `CORECORE_STREAM_SECONDS` | 90 | how much of a live stream the `stream` provider records per job |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` | | Reddit script-app credentials for the `reddit` provider |
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
| `GET /media/...` | clips and thumbnails (range requests supported) |

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
media/               created at runtime: segments/, thumbs/, inbox/, sources/, corecore.sqlite3 (git-ignored)
site/                output of `export` / `build-site` (git-ignored)
```
