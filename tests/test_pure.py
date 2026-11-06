"""Unit tests for the parts that need no network. Run: python -m unittest discover -s tests -v"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.parse
import unittest
from pathlib import Path

os.environ.setdefault("CORECORE_MEDIA", tempfile.mkdtemp(prefix="corecore-test-"))

from corecore import config, db, ffmpeg  # noqa: E402
from corecore.ingest import auto_tags  # noqa: E402
from corecore.providers.archive import choose_file  # noqa: E402
from corecore.providers.ytdlp import _entries  # noqa: E402


class ShotsTest(unittest.TestCase):
    def test_cuts_become_shots(self):
        shots = ffmpeg.shots_from_cuts(20.0, [5.0, 8.0, 19.5], min_len=1.2, max_len=8.0, edge_trim=0.1)
        starts = [round(s, 2) for s, _ in shots]
        self.assertEqual(starts, [0.1, 5.1, 8.1])  # the last 0.5 s shot is too short
        for _, length in shots:
            self.assertLessEqual(length, 8.0)

    def test_long_shot_is_carved(self):
        shots = ffmpeg.shots_from_cuts(60.0, [], min_len=1.2, max_len=8.0, max_chunks=4, edge_trim=0.0)
        self.assertEqual(len(shots), 4)
        self.assertEqual([round(l, 2) for _, l in shots], [8.0] * 4)
        self.assertAlmostEqual(shots[-1][0] + shots[-1][1], 60.0, places=2)

    def test_spread(self):
        self.assertEqual(ffmpeg.spread(list(range(100)), 4), [12, 37, 62, 87])
        self.assertEqual(ffmpeg.spread([1, 2, 3], 10), [1, 2, 3])


class TagTest(unittest.TestCase):
    def test_roundtrip(self):
        self.assertEqual(db.tags_to_db(" Nature, city,nature,, Old Ads "), ",nature,city,old-ads,")
        self.assertEqual(db.tags_from_db(",nature,city,"), ["nature", "city"])
        self.assertEqual(db.tags_to_db(None), ",")
        self.assertEqual(db.tags_from_db(","), [])

    def test_auto_tags(self):
        tags = auto_tags({"brightness": 0.1, "saturation": 0.05, "motion": 0.2}, {"has_audio": True, "width": 100, "height": 200}, -10)
        self.assertEqual(tags, ["dark", "muted", "motion", "audio", "loud", "vertical"])
        tags = auto_tags({"brightness": 0.7, "saturation": 0.5, "motion": 0.001}, {"has_audio": False, "width": 200, "height": 100}, None)
        self.assertEqual(tags, ["bright", "vivid", "still"])


class ArchiveTest(unittest.TestCase):
    def test_prefers_h264_then_smaller(self):
        files = [
            {"name": "a.ogv", "format": "Ogg Video", "size": "10"},
            {"name": "big.mp4", "format": "h.264", "size": str(10 ** 9)},
            {"name": "mid.mp4", "format": "MPEG4", "size": "5000"},
            {"name": "small.mp4", "format": "512Kb MPEG4", "size": "4000"},
            {"name": "ia.mp4", "format": "h.264 IA", "size": "9000"},
        ]
        self.assertEqual(choose_file(files)["name"], "ia.mp4")
        self.assertEqual(choose_file(files[:4])["name"], "small.mp4")
        self.assertIsNone(choose_file([{"name": "x.txt", "format": "Text", "size": "1"}]))
        # yt-dlp mirrors: no mp4 derivative, a .webm or .mkv original is fine (we re-encode anyway)
        mirror = [{"name": "abc.webm", "format": "WebM", "size": "300"}, {"name": "abc.mkv", "format": "Matroska", "size": "400"},
                  {"name": "abc.jpg", "format": "JPEG", "size": "5"}]
        self.assertEqual(choose_file(mirror)["name"], "abc.webm")
        self.assertEqual(choose_file(mirror + [{"name": "abc.mp4", "format": "h.264", "size": "900"}])["name"], "abc.mp4")


class YtDlpTest(unittest.TestCase):
    def test_entries_flatten(self):
        info = {"entries": [{"id": "a"}, None, {"entries": [{"id": "b"}, {"id": "c"}]}]}
        self.assertEqual([e["id"] for e in _entries(info)], ["a", "b", "c"])
        self.assertEqual(_entries({"id": "solo"}), [{"id": "solo"}])
        self.assertEqual(_entries(None), [])


class DbTest(unittest.TestCase):
    def test_seeded_sample_is_stable(self):
        db.init()
        with db.connect() as conn:
            conn.execute("INSERT INTO sources (provider, external_id, title) VALUES ('local', 'x', 't')")
            sid = conn.execute("SELECT id FROM sources WHERE external_id = 'x'").fetchone()["id"]
            for i in range(30):
                conn.execute("INSERT INTO clips (source_id, file, duration, tags) VALUES (?, ?, 3.0, ?)",
                             (sid, f"segments/{i}.mp4", ",nature," if i % 2 else ",city,"))
            a = [r["id"] for r in db.sample_clips(conn, n=10, seed=7)]
            b = [r["id"] for r in db.sample_clips(conn, n=10, seed=7)]
            c = [r["id"] for r in db.sample_clips(conn, n=10, seed=8)]
            self.assertEqual(a, b)
            self.assertNotEqual(a, c)
            nat = db.sample_clips(conn, n=50, tags=["nature"])
            self.assertTrue(all("nature" in db.tags_from_db(r["tags"]) for r in nat))
            excl = [r["id"] for r in db.sample_clips(conn, n=50, exclude=a)]
            self.assertFalse(set(excl) & set(a))
            conn.execute("DELETE FROM sources")


@unittest.skipUnless(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0, "ffmpeg missing")
class FfmpegRoundTrip(unittest.TestCase):
    def test_detect_cut_and_clip(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "src.mp4"
            norm = "format=yuv420p,fps=25,scale=320:180,setsar=1"
            subprocess.run([config.FFMPEG, "-y", "-loglevel", "error", "-t", "3", "-f", "lavfi", "-i", "smptebars=s=320x180:r=25",
                            "-t", "3", "-f", "lavfi", "-i", "mandelbrot=s=320x180:r=25",
                            "-filter_complex", f"[0:v]{norm}[a];[1:v]{norm}[b];[a][b]concat=n=2:v=1:a=0[v]",
                            "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast", str(src)], check=True)
            info = ffmpeg.probe(src)
            self.assertAlmostEqual(info["duration"], 6.0, delta=0.2)
            cuts = ffmpeg.detect_shots(src, threshold=0.3)
            self.assertTrue(any(2.5 < c < 3.5 for c in cuts), cuts)
            out = Path(d) / "clip.mp4"
            ffmpeg.cut_segment(src, 0.5, 2.0, out, height=180, has_audio=False)
            clip = ffmpeg.probe(out)
            self.assertAlmostEqual(clip["duration"], 2.0, delta=0.15)
            self.assertEqual(clip["height"], 180)
            stats = ffmpeg.frame_stats(out)
            self.assertTrue(0 <= stats["brightness"] <= 1)
            thumb = Path(d) / "t.jpg"
            ffmpeg.thumbnail(out, 0.5, thumb)
            self.assertGreater(thumb.stat().st_size, 500)


class HardBlockTest(unittest.TestCase):
    def test_hard_blocklist(self):
        for t in ("Hitler's speech at Siemens Dynamo factory", "Rare WW2 footage in colour", "Triumph of the Will (1935)",
                  "NAZI rally at Nuremberg", "Footage of the F\u00fchrer", "the Third Reich in colour"):
            self.assertTrue(config.hard_blocked(t), t)
            self.assertTrue(config.blocked_title(t), t)
        for t in ("Bison in Snow (pair)", "a warm day in Essex", "world wide web explained badly", "Fox Sparrow"):
            self.assertFalse(config.hard_blocked(t), t)
        # cruelty is never in the piece; uploader names match without their emoji
        self.assertTrue(config.hard_blocked("BLM animal (brutality) caught on camera"))
        self.assertTrue(config.hard_blocked("a description: the dog was abused for years"))
        self.assertTrue(config.blocked_source("Anything at all", "Ray Garcia \U0001F1FA\U0001F1F8"))
        self.assertTrue(config.blocked_title("Except dog crap. And violence. And Champ."))
        self.assertFalse(config.blocked_source("Kitten Wrasslin' on the bed", "Nina Paley"))

    def test_social_captions_are_read_by_the_general_blocklist(self):
        from corecore.providers.archive import caption_blocked
        # a mirrored post titled only "TikTok Video by <user>" carries its caption in the description
        self.assertTrue(caption_blocked("tiktok-7130942596586818818", "link in bio #nsfw #fyp"))
        self.assertTrue(caption_blocked("Instagram-DdeICa9AIqS", "Breaking news from the rally"))
        self.assertTrue(caption_blocked("twitter-1295991588083163136", "he got punched lol"))
        self.assertFalse(caption_blocked("tiktok-1", "a whole day alone in my flat #vlog #dayinmylife"))
        # a YouTube description is long and full of links and sponsor copy: the mirror stays judged by titles
        self.assertFalse(caption_blocked("youtube-FtWXWKUK6rg", "subscribe for more reviews and news"))

    def test_put_back_sources_are_not_banned(self):
        from corecore import seeds
        idents = {f"{j['provider']}:{j['url'].rsplit('/', 1)[-1]}" for j in seeds.REINSTATED}
        self.assertFalse(idents & config.BANNED_SOURCES)
        self.assertTrue(all("modern" in j["tags"] for j in seeds.REINSTATED))
        for title, uploader in (("Una 'dashcam' graba el momento exacto en que cae un proyectil en Ucrania", "el OJO en"),
                                ("Suspect Crashes into Police Cruisers & Attempts To Flee (Dashcam Video)", "Law&Crime Network"),
                                ("A Plane Hit the Pentagon, Baby Steps for the Parrots of Loose Change etc", "Ryan Dawson Fan"),
                                ("IRAN STRIKES 6 AIRCRAFT IN 24 HOURS", "Jackson Hinkle Official")):
            self.assertFalse(config.blocked_source(title, uploader), title)

    def test_audit_removes_hitler_footage_from_the_pool(self):
        from corecore import audit as audit_mod, seeds
        with db.connect() as conn:
            conn.execute("DELETE FROM sources")
            for ext, title, uploader, provider in (("speech", "Hitler's speech at Siemens Dynamo factory", "Blitz", "archive"),
                                                   ("compilation", "The 20th century in ten minutes", "a history channel", "archive"),
                                                   ("heron", "Great Blue Heron Flying", "Katja Schulz", "archive"),
                                                   ("walk", "Night walk in the rain", "someone", "ytdlp"),
                                                   ("twitter-1295991588083163136", "a clip", "someone", "archive"),
                                                   ("retired", "a doorbell clip", "someone", "archive")):
                query = seeds.RETIRED_QUERIES[0] if ext == "retired" else "q"
                conn.execute("INSERT INTO sources (provider, external_id, url, title, uploader, status, tags, query) "
                             "VALUES (?, ?, 'u', ?, ?, 'done', ',modern,', ?)", (provider, ext, title, uploader, query))
                sid = conn.execute("SELECT id FROM sources WHERE external_id = ?", (ext,)).fetchone()["id"]
                (config.SEGMENTS_DIR / f"{ext}.mp4").write_bytes(b"x")
                (config.THUMBS_DIR / f"{ext}.jpg").write_bytes(b"x")
                conn.execute("INSERT INTO clips (source_id, file, thumb, duration, width, height, tags) "
                             "VALUES (?, ?, ?, 1.0, 16, 9, ',modern,')", (sid, f"segments/{ext}.mp4", f"thumbs/{ext}.jpg"))
        lookups = []

        def fetch(ident):
            lookups.append(ident)
            if ident == "compilation":   # the title does not name him; the description does
                return {"description": "archive footage of the century, including Adolf Hitler at a rally", "subject": ["history"]}
            return {"description": "a heron over the marsh", "subject": ["birds"]}

        r = audit_mod.audit(fetch=fetch, workers=2, log=lambda m: None)
        self.assertEqual((r["sources_removed"], r["clips_removed"]), (4, 4))   # by title, by description, by hand, by query
        self.assertEqual(sorted(lookups), ["compilation", "heron"])   # the speech fell on its title; the yt-dlp walk has nothing to look up
        with db.connect() as conn:
            banned = {row["external_id"]: row["banned"] for row in
                      conn.execute("SELECT s.external_id, c.banned FROM clips c JOIN sources s ON s.id = c.source_id")}
        self.assertEqual(banned, {"speech": 1, "compilation": 1, "heron": 0, "walk": 0, "twitter-1295991588083163136": 1, "retired": 1})
        self.assertFalse((config.SEGMENTS_DIR / "speech.mp4").exists())
        self.assertFalse((config.THUMBS_DIR / "compilation.jpg").exists())
        self.assertTrue((config.SEGMENTS_DIR / "heron.mp4").exists())
        lookups.clear()
        self.assertEqual(audit_mod.audit(fetch=fetch, log=lambda m: None)["looked_up"], 0)   # each item is looked up once
        self.assertEqual(lookups, [])
        with db.connect() as conn:
            conn.execute("DELETE FROM sources")


if __name__ == "__main__":
    unittest.main()


class ExportTest(unittest.TestCase):
    def test_select_clips_round_robin_and_budget(self):
        from corecore.export import select_clips
        with tempfile.TemporaryDirectory() as d:
            media = Path(d)
            (media / "segments").mkdir()
            rows = []
            for sid in (1, 2, 3):
                for i in range(4):
                    f = f"segments/{sid}_{i}.mp4"
                    (media / f).write_bytes(b"x" * 100)
                    rows.append({"id": sid * 10 + i, "source_id": sid, "file": f, "start": i})
            chosen, total = select_clips(rows, media, max_bytes=650, max_clips=100)
            self.assertEqual(len(chosen), 6)
            self.assertEqual(total, 600)
            self.assertEqual(sorted({r["source_id"] for r in chosen}), [1, 2, 3])  # spread across sources
            chosen, _ = select_clips(rows, media, max_bytes=10 ** 9, max_clips=5)
            self.assertEqual(len(chosen), 5)

    def test_bans_from_the_live_site_are_left_out_of_the_export(self):
        from corecore.export import export_site
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "bans.txt"
            f.write_text("# bans from example.org\n"
                         "archive:tiktok-1@12.5   # a clip\n"
                         "archive:twitter-9        # a whole source\n"
                         "not a line\narchive:tiktok-1@x\n")
            bans = config.read_bans(f)
            self.assertEqual(bans, ({"archive:twitter-9"}, {"archive:tiktok-1": [12.5]}))
            self.assertTrue(config.banned_clip("archive:tiktok-1", 12.53, bans))
            self.assertFalse(config.banned_clip("archive:tiktok-1", 13.0, bans))
            self.assertFalse(config.banned_clip("archive:tiktok-1", None, bans))
            self.assertTrue(config.banned_clip("archive:twitter-9", 0.0, bans))
            self.assertEqual(config.read_bans(Path(d) / "missing.txt"), (set(), {}))
        db.init()
        with db.connect() as conn:
            conn.execute("DELETE FROM sources")
            conn.execute("INSERT INTO sources (provider, external_id, url, title, status, tags) VALUES "
                         "('archive', 'tiktok-1', 'https://archive.org/details/tiktok-1', 'a day in my life', 'done', ',modern,')")
            sid = conn.execute("SELECT id FROM sources WHERE external_id = 'tiktok-1'").fetchone()["id"]
            for i, start in enumerate((0.0, 12.5)):
                seg = config.SEGMENTS_DIR / f"ban_{i}.mp4"
                subprocess.run([config.FFMPEG, "-y", "-loglevel", "error", "-t", "1", "-f", "lavfi", "-i", "testsrc=s=160x90:r=10",
                                "-c:v", "libx264", "-preset", "ultrafast", str(seg)], check=True)
                conn.execute("INSERT INTO clips (source_id, file, start, duration, width, height, has_audio, tags) VALUES "
                             "(?, ?, ?, 1.0, 160, 90, 0, ',modern,')", (sid, f"segments/ban_{i}.mp4", start))
        saved = config.BANS
        try:
            with tempfile.TemporaryDirectory() as d:
                config.BANS = (set(), {})
                m = export_site(Path(d) / "all", log=lambda x: None)
                self.assertEqual(m["clips"], 2)
                manifest = json.loads((Path(d) / "all" / "manifest.json").read_text())
                self.assertEqual(manifest["sources"][0]["key"], "archive:tiktok-1")   # what [ copy bans ] names
                self.assertEqual(sorted(c["start"] for c in manifest["clips"]), [0.0, 12.5])
                config.BANS = (set(), {"archive:tiktok-1": [12.5]})
                self.assertEqual(export_site(Path(d) / "one", log=lambda x: None)["clips"], 1)
                config.BANS = ({"archive:tiktok-1"}, {})
                self.assertEqual(export_site(Path(d) / "none", log=lambda x: None)["clips"], 0)
        finally:
            config.BANS = saved

    def test_export_site_writes_manifest(self):
        from corecore.export import export_site
        db.init()
        with db.connect() as conn:
            conn.execute("DELETE FROM sources")
            conn.execute("INSERT INTO sources (provider, external_id, url, title, status, tags) VALUES "
                         "('local', 'exp', 'file:///x', 'Design for Dreaming (1956)', 'done', ',archive,ads,')")
            sid = conn.execute("SELECT id FROM sources WHERE external_id = 'exp'").fetchone()["id"]
            seg = config.SEGMENTS_DIR / "exp_000.mp4"
            subprocess.run([config.FFMPEG, "-y", "-loglevel", "error", "-t", "1", "-f", "lavfi", "-i", "testsrc=s=160x90:r=10",
                            "-c:v", "libx264", "-preset", "ultrafast", str(seg)], check=True)
            conn.execute("INSERT INTO clips (source_id, file, thumb, duration, width, height, has_audio, tags) VALUES "
                         "(?, 'segments/exp_000.mp4', NULL, 1.0, 160, 90, 0, ',archive,ads,bright,')", (sid,))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "site"
            summary = export_site(out, log=lambda m: None)
            self.assertEqual(summary["clips"], 1)
            self.assertEqual(export_site(Path(d) / "none", tags=["modern"], log=lambda m: None)["clips"], 0)
            self.assertEqual(export_site(Path(d) / "some", tags=["ads", "modern"], log=lambda m: None)["clips"], 1)
            with db.connect() as conn:  # a source whose title is now on the blocklist is not exported
                conn.execute("UPDATE sources SET title = 'Concert hall attack RAW VIDEO [GRAPHIC]' WHERE external_id = 'exp'")
            self.assertEqual(export_site(Path(d) / "blocked", log=lambda m: None)["clips"], 0)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["sources"][0]["title"], "Design for Dreaming (1956)")
            self.assertEqual(manifest["clips"][0]["file"], "clips/exp_000.mp4")
            self.assertTrue((out / "clips" / "exp_000.mp4").exists())
            self.assertTrue((out / "web" / "app.js").exists())
            self.assertIn('window.CORECORE_STATIC = "manifest.json"', (out / "index.html").read_text())
            # one version on every address, so a CDN never mixes scripts from two deploys
            page, app = (out / "index.html").read_text(), (out / "web" / "app.js").read_text()
            v = page.split('src="web/app.js?v=', 1)[1].split('"', 1)[0]
            self.assertIn(f'href="web/styles.css?v={v}"', page)
            self.assertIn(f"from './audio.js?v={v}'", app)
            self.assertNotRegex(app, r"from '\./[a-z]+\.js'")
            self.assertTrue((out / ".nojekyll").exists())
        with db.connect() as conn:
            conn.execute("DELETE FROM sources")


class StarterBudgetTest(unittest.TestCase):
    def test_run_starter_jobs_respects_time_budget(self):
        from corecore import jobs, seeds
        db.init()
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "tiny.mp4"
            subprocess.run([config.FFMPEG, "-y", "-loglevel", "error", "-t", "3", "-f", "lavfi", "-i", "testsrc2=s=160x90:r=10",
                            "-c:v", "libx264", "-preset", "ultrafast", str(src)], check=True)
            seeds.SEED_SETS["test"] = [{"provider": "local", "url": str(src), "max_items": 1, "tags": ["t"]}]
            config.LOCAL_ROOTS.append(Path(d))
            try:
                none = jobs.run_starter_jobs(time_budget=0, seed_set="test")
                self.assertEqual(none["jobs"], 0)
                self.assertTrue(none["stopped_early"])
                done = jobs.run_starter_jobs(time_budget=120, seed_set="test")
                self.assertEqual(done["jobs"], 1)
                self.assertGreaterEqual(done["clips"], 1)
            finally:
                del seeds.SEED_SETS["test"]
                config.LOCAL_ROOTS.remove(Path(d))
                with db.connect() as conn:
                    conn.execute("DELETE FROM sources")
                    conn.execute("DELETE FROM jobs")


def _tiny_video(path: Path, seconds: int = 3) -> None:
    subprocess.run([config.FFMPEG, "-y", "-loglevel", "error", "-t", str(seconds), "-f", "lavfi", "-i", "testsrc2=s=160x90:r=10",
                    "-c:v", "libx264", "-preset", "ultrafast", str(path)], check=True)


class ReviewRegressionTest(unittest.TestCase):
    """Regressions for the defects found in the first code review."""

    def test_local_provider_refuses_paths_outside_allowed_roots(self):
        from corecore.providers.local import LocalProvider
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "outside.mp4"
            _tiny_video(src)
            with self.assertRaises(Exception):
                LocalProvider().search(None, str(src), 1)
            (Path(d) / "code.ts").write_text("export const x = 1;")
            config.LOCAL_ROOTS.append(Path(d))
            try:
                cands = LocalProvider().search(None, d, 0)
                self.assertEqual([Path(c.external_id).name for c in cands], ["outside.mp4"])  # .ts is not video
            finally:
                config.LOCAL_ROOTS.remove(Path(d))

    def test_cancelled_ingest_leaves_source_pending(self):
        from corecore.ingest import ingest_candidate
        from corecore.providers import Candidate
        db.init()
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "v.mp4"
            _tiny_video(src)
            cand = Candidate("local", str(src), src.as_uri(), title="v", extra={"keep": True})
            added = ingest_candidate(cand, ["t"], logger=lambda m: None, should_cancel=lambda: True)
            self.assertEqual(added, 0)
            with db.connect() as conn:
                row = conn.execute("SELECT status FROM sources WHERE external_id = ?", (str(src),)).fetchone()
                self.assertEqual(row["status"], "pending")
                added = ingest_candidate(cand, ["t"], logger=lambda m: None)
                self.assertGreaterEqual(added, 1)
                row = conn.execute("SELECT status FROM sources WHERE external_id = ?", (str(src),)).fetchone()
                self.assertEqual(row["status"], "done")
                conn.execute("DELETE FROM sources")

    def test_tag_filters_escape_like_wildcards(self):
        db.init()
        with db.connect() as conn:
            conn.execute("INSERT INTO sources (provider, external_id, title, status) VALUES ('local', 'like', 't', 'done')")
            sid = conn.execute("SELECT id FROM sources WHERE external_id = 'like'").fetchone()["id"]
            conn.execute("INSERT INTO clips (source_id, file, duration, tags) VALUES (?, 'segments/l.mp4', 1, ',city,')", (sid,))
            self.assertEqual(len(db.sample_clips(conn, n=10, tags=["%"])), 0)
            self.assertEqual(len(db.sample_clips(conn, n=10, tags=["cit_"])), 0)
            self.assertEqual(len(db.sample_clips(conn, n=10, tags=["City"])), 1)
            self.assertEqual(db.tag_like("a_b%"), "%,a\\_b\\%,%")
            conn.execute("DELETE FROM sources")

    def test_exclude_parsing_never_raises(self):
        from corecore.app import _parse_ids
        self.assertEqual(_parse_ids("1, 2,x,--3,²,99999999999999999999999"), [1, 2])
        self.assertIsNone(_parse_ids(""))
        self.assertIsNone(_parse_ids("abc"))

    def test_archive_search_error_is_an_error(self):
        from corecore.providers import archive
        original = archive._get_json
        archive._get_json = lambda url, timeout=60: {"error": "a token is at an unexpected position"}
        try:
            with self.assertRaises(archive.ProviderError):
                archive.ArchiveProvider().search("collection:prelinger AND )", None, 3)
        finally:
            archive._get_json = original

    def test_worker_only_requeues_dead_owners(self):
        from corecore.jobs import owner_alive, owner_token
        self.assertTrue(owner_alive("otherhost:1"))      # cannot check another host: assume alive
        self.assertFalse(owner_alive(None))
        self.assertFalse(owner_alive(owner_token()))      # our own pid is not "another live owner"
        self.assertFalse(owner_alive(f"{owner_token().rsplit(':', 1)[0]}:999999"))

    def test_media_mount_does_not_expose_database(self):
        from corecore.app import app
        paths = [r.path for r in app.routes]
        self.assertIn("/media/segments", paths)
        self.assertNotIn("/media", paths)


class ContemporaryTest(unittest.TestCase):
    def test_blocklist(self):
        self.assertTrue(config.blocked_title("GIRL GETS NAKED ON CAM FOR YOUTUBE"))
        self.assertFalse(config.blocked_title("Shibuya New Year Walk 4K"))
        self.assertFalse(config.blocked_title(None))
        self.assertTrue(config.blocked_title("Russia's NEW Anti-Drone Tanks Just Entered Combat"))
        self.assertTrue(config.blocked_title("Moscow concert hall attack - RAW VIDEO [GRAPHIC]"))
        # off-topic material found by innocent words on the mirror: games, manga dubs, news, politics, products
        for junk in ("What Neil DeGrasse Tyson Likes About Starry Night Joe Rogan Podcast", "[Manga Dub] I reunited with my childhood friend",
                     "CBS EVENING NEWS (12/31/1988): The Fog Bowl", "Hillary Clinton and DNC Paid for the Dossier",
                     "Satisfyer Pro 2 Modern Blossom ASMR Product Review", "SPIDER-MAN: NO WAY HOME | Heroes Reunited Featurette"):
            self.assertTrue(config.blocked_title(junk), junk)
        for fine in ("Russian dashcam compilation, winter", "4K Forest Walk in the Rain", "warm light in the kitchen",
                     "Switching on the trailcams #camera #trailcam #wildlife", "One Act of Kindness, 10 Years Later"):
            self.assertFalse(config.blocked_title(fine), fine)
        # the uploader counts too: a channel called "... News", or an account on the blocked list
        self.assertTrue(config.blocked_source("Cute kitten runs to police", "Breitbart News"))
        self.assertTrue(config.blocked_source("Police are examining CCTV footage", "SkyNews"))
        self.assertTrue(config.blocked_title("Star Fox - Corneria Full Level Gameplay"))
        self.assertTrue(config.blocked_source("We grilled a dog outside a BBQ spot", "officialpeta"))
        self.assertFalse(config.blocked_source("We grilled a dog outside a BBQ spot", "a neighbour"))
        self.assertFalse(config.blocked_source("Snow on the allotment", None))
        # what the second beauty scrape let through, and what it should keep
        for junk in ("sunset flower meme 21 Jan 2020", "Majestic sunset c17 take-off RAF Lakenheath",
                     "Black Box Recorders recovered from Sunset Limited Engines", "No snow day #comedy #shorts",
                     "#silent #fox #cute #play #3d", "20161127 - 172238 - Badger - Attempted coitus - 0177"):
            self.assertTrue(config.blocked_title(junk), junk)
        self.assertTrue(config.blocked_source("MY BULLY ADOPTED ME", "cute noob"))
        for fine in ("Bison in Snow (pair) (Yellowstone National Park, NPS video)", "Dogs in Fog", "Waves rolling in",
                     "Hummingbird Making Nest", "Minute Out In It: Morning Fog (Yellowstone National Park, NPS video)",
                     "Kelp Forest SlowMix, Monterey Bay Aquarium, California"):
            self.assertFalse(config.blocked_title(fine), fine)

    def test_archive_page_wraps_for_small_result_sets(self):
        # the build rotates the results page weekly; a query with 41 results has no page 3, so it wraps to page 1
        from corecore.providers import archive
        calls = []
        def fake(url):
            q = dict(urllib.parse.parse_qsl(url.split("?", 1)[1]))
            calls.append(int(q["page"]))
            docs = [] if int(q["page"]) > 2 else [{"identifier": f"cam-{q['page']}-{i}", "title": f"Trail camera {i}"} for i in range(3)]
            return {"response": {"numFound": 41, "docs": docs}}
        old_get, old_env = archive._get_json, os.environ.get("CORECORE_ARCHIVE_PAGE")
        archive._get_json, os.environ["CORECORE_ARCHIVE_PAGE"] = fake, "3"
        try:
            cands = archive.ArchiveProvider().search('title:("trail cam")', None, 8)
        finally:
            archive._get_json = old_get
            if old_env is None: os.environ.pop("CORECORE_ARCHIVE_PAGE", None)
            else: os.environ["CORECORE_ARCHIVE_PAGE"] = old_env
        self.assertEqual(calls, [3, 1])            # 41 results in pages of 24: page 3 wraps to page 1
        self.assertEqual([c.external_id for c in cands], ["cam-1-0", "cam-1-1", "cam-1-2"])
        for ok in ("a warm day in Essex", "software demo at the fair", "award show vlog", "stripes on my cat", "sex pistols cover"):
            self.assertEqual(config.blocked_title(ok), ok.startswith("sex"), ok)   # whole words only

    def test_ytdlp_pasted_links_become_candidates(self):
        from corecore.providers.ytdlp import YtDlpProvider
        cands = YtDlpProvider().search(None, "https://www.tiktok.com/@a/video/1\nhttps://youtu.be/xyz https://vimeo.com/1", 0)
        self.assertEqual([c.url for c in cands], ["https://www.tiktok.com/@a/video/1", "https://youtu.be/xyz", "https://vimeo.com/1"])
        self.assertEqual(len(YtDlpProvider().search(None, "https://youtu.be/a https://youtu.be/b", 1)), 1)

    def test_archive_sort_suffix(self):
        from corecore.providers import archive
        seen = {}
        archive._get_json = (lambda orig: lambda url, timeout=60: (seen.setdefault("url", url), {"response": {"docs": []}})[1])(archive._get_json)
        try:
            archive.ArchiveProvider().search('collection:mirrortube AND title:(vlog) |sort=date desc', None, 2)
            self.assertIn("sort%5B%5D=date+desc", seen["url"])
            self.assertNotIn("%7Csort", seen["url"])
        finally:
            import importlib
            importlib.reload(archive)

    def test_pages_for_a_deeper_run(self):
        from corecore.jobs import parse_pages
        self.assertEqual(parse_pages("1,2,4"), ["1", "2", "4"])
        self.assertEqual(parse_pages(" 5 6,5 "), ["5", "6"])
        self.assertEqual(parse_pages(""), [None])
        self.assertEqual(parse_pages("0,x"), [None])
        from corecore import seeds
        self.assertTrue(seeds.TWITTER_JOBS and all(j in seeds.INTERNET_JOBS for j in seeds.TWITTER_JOBS))

    def test_build_site_takes_each_page_in_turn(self):
        import os
        from unittest import mock
        from corecore import __main__ as cli, audit as audit_mod, export as export_mod, jobs as jobs_mod
        seen = []
        def fake_run(budget, echo=None, seed_set="contemporary"):
            seen.append((os.environ.get("CORECORE_ARCHIVE_PAGE"), seed_set, budget > 0))
            return {"jobs": 0, "clips": 0}
        saved = os.environ.get("CORECORE_ARCHIVE_PAGE")
        try:
            with mock.patch.object(jobs_mod, "run_starter_jobs", fake_run), \
                 mock.patch.object(jobs_mod, "run_reinstated", lambda echo=None: {}), \
                 mock.patch.object(audit_mod, "audit", lambda log=print: {}), \
                 mock.patch.object(export_mod, "export_site", lambda *a, **k: {}):
                with tempfile.TemporaryDirectory() as d:
                    cli.main(["build-site", "--out", d, "--set", "twitter", "--time-budget", "60", "--pages", "1,2,4"])
                    self.assertEqual(seen, [("1", "twitter", True), ("2", "twitter", True), ("4", "twitter", True)])
                    seen.clear()
                    os.environ["CORECORE_ARCHIVE_PAGE"] = "3"
                    cli.main(["build-site", "--out", d, "--set", "internet", "--time-budget", "60"])
                    self.assertEqual(seen, [("3", "internet", True)])   # no --pages: this week's page, as before
        finally:
            if saved is None:
                os.environ.pop("CORECORE_ARCHIVE_PAGE", None)
            else:
                os.environ["CORECORE_ARCHIVE_PAGE"] = saved

    def test_seed_sets(self):
        from corecore import seeds
        self.assertEqual(set(seeds.SEED_SETS), {"contemporary", "internet", "twitter", "beauty", "archival", "all"})
        self.assertTrue(seeds.INTERNET_JOBS and all("modern" in j["tags"] and j["provider"] == "archive" for j in seeds.INTERNET_JOBS))
        self.assertTrue(all(j in seeds.CONTEMPORARY_JOBS for j in seeds.INTERNET_JOBS))   # weekly builds keep them in rotation
        self.assertTrue(all("beauty" in j["tags"] for j in seeds.BEAUTY_JOBS) and len(seeds.BEAUTY_JOBS) >= 10)
        self.assertTrue(all(j["provider"] in ("archive", "dailymotion") for j in seeds.CONTEMPORARY_JOBS))


class NewProvidersTest(unittest.TestCase):
    def test_stream_candidates(self):
        from corecore.providers.stream import StreamProvider
        cands = StreamProvider().search(None, "https://cam.example.org/live/index.m3u8\nrtsp://10.0.0.5/stream junk", 0)
        self.assertEqual([c.url for c in cands], ["https://cam.example.org/live/index.m3u8", "rtsp://10.0.0.5/stream"])
        self.assertEqual(cands[0].uploader, "cam.example.org")
        with self.assertRaises(Exception):
            StreamProvider().search("not a url", None, 1)

    def test_reddit_needs_credentials_and_filters_posts(self):
        from corecore.providers import reddit
        os.environ.pop("REDDIT_CLIENT_ID", None)
        with self.assertRaises(reddit.ProviderError):
            reddit.RedditProvider().search("dashcam", None, 3)
        posts = [
            {"data": {"id": "a", "is_video": True, "over_18": False, "title": "dashcam near miss", "permalink": "/r/dashcam/comments/a/x/",
                      "subreddit": "dashcam", "secure_media": {"reddit_video": {"fallback_url": "https://v.redd.it/abc/DASH_720.mp4?source=fallback", "duration": 20}}}},
            {"data": {"id": "b", "is_video": True, "over_18": True, "title": "nope", "secure_media": {"reddit_video": {"fallback_url": "https://v.redd.it/b/DASH_720.mp4"}}}},
            {"data": {"id": "c", "is_video": False, "title": "image post"}},
        ]
        cands = reddit._candidates_from_posts(posts, 0)
        self.assertEqual([c.external_id for c in cands], ["a"])
        self.assertEqual(cands[0].extra["video"], "https://v.redd.it/abc/DASH_720.mp4")
        self.assertEqual(cands[0].uploader, "r/dashcam")
