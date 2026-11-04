"""Unit tests for the parts that need no network. Run: python -m unittest discover -s tests -v"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
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
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["sources"][0]["title"], "Design for Dreaming (1956)")
            self.assertEqual(manifest["clips"][0]["file"], "clips/exp_000.mp4")
            self.assertTrue((out / "clips" / "exp_000.mp4").exists())
            self.assertTrue((out / "web" / "app.js").exists())
            self.assertIn('window.CORECORE_STATIC = "manifest.json"', (out / "index.html").read_text())
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

    def test_seed_sets(self):
        from corecore import seeds
        self.assertEqual(set(seeds.SEED_SETS), {"contemporary", "archival", "all"})
        self.assertTrue(all(j["provider"] in ("archive", "dailymotion") for j in seeds.CONTEMPORARY_JOBS))
