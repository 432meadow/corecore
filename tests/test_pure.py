"""Unit tests for the parts that need no network. Run: python -m unittest discover -s tests -v"""
from __future__ import annotations

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
        self.assertIsNone(choose_file([{"name": "x.avi", "format": "AVI", "size": "1"}]))


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
