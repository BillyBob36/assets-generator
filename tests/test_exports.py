import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

import app


class ExportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.storage = Path(temporary.name)
        folder = self.storage / "jobs" / "example"
        folder.mkdir(parents=True)
        image = Image.new("RGBA", (6, 5))
        image.putpixel((1, 1), (255, 0, 0, 255))
        image.putpixel((3, 2), (255, 0, 0, 128))
        self.original = folder / "result.png"
        image.save(self.original)
        self.original_bytes = self.original.read_bytes()
        job = {"status": "succeeded", "params": {"icon_label": "test", "material_id": "gold"}}
        for name, value in {
            "AUTH_ENABLED": False,
            "JOBS": {"example": job},
            "JOBS_DIR": self.storage / "jobs",
            "EXPORT_COLORS_PATH": self.storage / "export-colors.json",
        }.items():
            patcher = patch.object(app, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(app.app)
        self.addCleanup(self.client.close)

    def export(self, **params):
        response = self.client.get("/api/jobs/example/result.png", params=params)
        self.assertEqual(response.status_code, 200)
        return Image.open(io.BytesIO(response.content)).convert("RGBA")

    def test_transparent_export_keeps_original_bytes(self):
        response = self.client.get("/api/jobs/example/result.png")
        self.assertEqual(response.content, self.original_bytes)
        self.assertEqual(self.export(background="transparent").getpixel((0, 0)), (0, 0, 0, 0))

    def test_composition_preserves_edges_and_original(self):
        image = self.export(background="#0000ff")
        self.assertEqual(image.size, (6, 5))
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 255, 255))
        self.assertEqual(image.getpixel((1, 1)), (255, 0, 0, 255))
        self.assertEqual(image.getpixel((3, 2)), (128, 0, 127, 255))
        self.assertEqual(self.original.read_bytes(), self.original_bytes)

    def test_crop_precedes_composition_and_keeps_alpha(self):
        for mode, size in [("rectangle", (3, 2)), ("square", (3, 3))]:
            transparent = self.export(crop=mode)
            self.assertEqual(transparent.size, size)
            self.assertEqual(transparent.getpixel((2, 1)), (255, 0, 0, 128))
            opaque = self.export(crop=mode, background="#0000FF")
            self.assertEqual(opaque.size, size)
            self.assertEqual(opaque.getpixel((2, 1)), (128, 0, 127, 255))

    def test_recent_colors_are_persistent_unique_and_limited_to_ten(self):
        self.assertEqual(self.client.get("/api/export-colors").json(), {"colors": []})
        for index in range(12):
            response = self.client.post("/api/export-colors", json={"color": f"#{index:06x}"})
            self.assertEqual(response.status_code, 200)
        self.client.post("/api/export-colors", json={"color": "#000009"})
        colors = self.client.get("/api/export-colors").json()["colors"]
        self.assertEqual(len(colors), 10)
        self.assertEqual(len(set(colors)), 10)
        self.assertEqual(colors[:2], ["#000009", "#00000B"])
        self.assertEqual(json.loads(app.EXPORT_COLORS_PATH.read_text()), colors)

    def test_invalid_colors_and_auth(self):
        for color in ["red", "##123456", "#12345G", "../file", "#12345678"]:
            self.assertEqual(self.client.post("/api/export-colors", json={"color": color}).status_code, 400)
            self.assertEqual(self.client.get("/api/jobs/example/result.png", params={"background": color}).status_code, 400)
        self.assertFalse(app.EXPORT_COLORS_PATH.exists())
        with patch.object(app, "AUTH_ENABLED", True):
            self.assertEqual(self.client.get("/api/export-colors").status_code, 401)
            self.assertEqual(self.client.post("/api/export-colors", json={"color": "#FFFFFF"}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
