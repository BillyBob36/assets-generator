import asyncio
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

import app


def png(image):
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


class UploadTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name, value in {"JOBS": {}, "JOBS_DIR": self.root,
                            "job_queue": asyncio.Queue(), "AUTH_ENABLED": False}.items():
            patcher = patch.object(app, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(app.app)
        self.addCleanup(self.client.close)
        self.small = png(Image.new("RGBA", (16, 12), (150, 60, 200, 128)))

    def post(self, image=None, source=None):
        files = {"image": ("icon.png", image if image is not None else self.small, "image/png")}
        if source is not None:
            files["source_image"] = ("source.png", source, "image/png")
        return self.client.post("/api/jobs", files=files, data={
            "material_id": "gold", "icon_id": "custom:example", "icon_label": "example"})

    def test_large_binary_source_is_resized_persisted_and_served_for_reruns(self):
        # Real incompressible pixels reproduce the old >1 MB text-part problem.
        source = png(Image.frombytes("RGBA", (2600, 1300), os.urandom(2600 * 1300 * 4)))
        self.assertGreater(len(source), 8 * 1024 * 1024)
        response = self.post(image=source, source=source)
        self.assertEqual(response.status_code, 200, response.text)
        job_id = response.json()["id"]
        summary = self.client.get(f"/api/jobs/{job_id}").json()
        self.assertEqual(summary["icon_svg_url"], f"/api/jobs/{job_id}/source.png")
        self.assertLess(len(json.dumps(summary)), 2000)
        for name in ("input.png", "source.png"):
            with Image.open(self.root / job_id / name) as im:
                self.assertEqual(im.size, (1536, 768))
                self.assertEqual(im.mode, "RGBA")
        saved = (self.root / job_id / "source.png").read_bytes()
        self.assertEqual(self.client.get(summary["icon_svg_url"]).content, saved)
        app.JOBS.clear()
        app._rehydrate_jobs()
        self.assertEqual(self.client.get(summary["icon_svg_url"]).content, saved)
        with patch.object(app, "AUTH_ENABLED", True):
            self.assertEqual(self.client.get(summary["icon_svg_url"]).status_code, 401)

    def test_normalization_retains_alpha_color_and_exif_orientation(self):
        im = Image.open(io.BytesIO(app._normalize_uploaded_image(self.small)))
        self.assertEqual(im.size, (16, 12))
        self.assertEqual(im.getpixel((0, 0)), (150, 60, 200, 128))
        original = Image.new("RGB", (30, 10), "red")
        exif = Image.Exif()
        exif[274] = 6
        encoded = io.BytesIO()
        original.save(encoded, "JPEG", exif=exif)
        corrected = Image.open(io.BytesIO(app._normalize_uploaded_image(encoded.getvalue())))
        self.assertEqual(corrected.size, (10, 30))
        self.assertNotIn(274, corrected.getexif())

    def test_invalid_empty_and_oversized_files_do_not_queue_jobs(self):
        for raw in (b"", b"not an image"):
            self.assertEqual(self.post(image=raw).status_code, 400)
        self.assertEqual(self.post(source=b"invalid source").status_code, 400)
        with patch.object(app, "MAX_UPLOAD_BYTES", 4096):
            self.assertEqual(self.post(image=b"x" * 4097).status_code, 413)
        self.assertEqual(app.JOBS, {})
        self.assertTrue(app.job_queue.empty())

    def test_custom_job_without_source_keeps_input_preview_and_missing_source_is_clear(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        job_id = response.json()["id"]
        self.assertEqual(app.JOBS[job_id]["icon_svg_url"], f"/api/jobs/{job_id}/input.png")
        self.assertEqual(self.client.get(f"/api/jobs/{job_id}/source.png").status_code, 410)
        self.assertEqual(self.client.get("/api/jobs/missing/source.png").status_code, 404)


if __name__ == "__main__":
    unittest.main()
