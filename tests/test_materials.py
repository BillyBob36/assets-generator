import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

import app
import generate_previews
from materials import MATERIALS, build_prompt


class ChildlikeMaterialTests(unittest.TestCase):
    def test_prompt_separates_subject_and_style(self):
        prompt = build_prompt("childlike_sketch", "calendar-month-outline")
        self.assertIn('"calendar month outline"', prompt)
        self.assertIn("IMAGE 1 is the CONTENT reference", prompt)
        self.assertIn("IMAGE 2 is ONLY the STYLE reference", prompt)
        self.assertIn("EIGHT-YEAR-OLD", prompt)
        self.assertNotIn("LITERAL STENCIL", prompt)
        self.assertIn("LITERAL STENCIL", build_prompt("gold", "calendar"))

    def test_black_ink_removes_white_and_noise_but_keeps_soft_edges(self):
        image = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
        image.putpixel((16, 16), (0, 0, 0, 255))
        image.putpixel((17, 16), (128, 128, 128, 255))
        image.putpixel((18, 16), (0, 0, 0, 100))
        image.putpixel((0, 0), (0, 0, 0, 6))
        output = app._black_ink_only(image)
        self.assertEqual(output.getpixel((16, 16)), (0, 0, 0, 255))
        self.assertEqual(output.getpixel((17, 16)), (0, 0, 0, 127))
        self.assertEqual(output.getpixel((18, 16)), (0, 0, 0, 100))
        self.assertEqual(output.getpixel((0, 0)), (0, 0, 0, 0))
        self.assertEqual(output.getpixel((31, 31)), (0, 0, 0, 0))

    def test_generation_sends_style_only_for_selected_material(self):
        output = io.BytesIO()
        Image.new("RGBA", (32, 32), (200, 100, 50, 128)).save(output, format="PNG")
        response = Mock(status_code=200)
        response.json.return_value = {"data": [{"b64_json": base64.b64encode(output.getvalue()).decode()}]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "example").mkdir()
            (root / "example" / "input.png").write_bytes(output.getvalue())
            with patch.object(app, "JOBS_DIR", root), patch.object(app, "_azure_post_with_retry", return_value=response) as call:
                for material in ("childlike_sketch", "gold"):
                    result = app._do_generation({"id": "example", "params": {
                        "material_id": material, "icon_label": "calendar", "quality": "medium",
                        "ratio": "1:1", "width": 32, "height": 32,
                    }})
                    files = call.call_args.args[3]
                    image = Image.open(io.BytesIO(result))
                    if material == "childlike_sketch":
                        self.assertEqual([field for field, _ in files], ["image[]", "image[]"])
                        self.assertEqual(files[0][1][0], "icon.png")
                        self.assertEqual(files[1][1][0], "style-reference.png")
                        self.assertEqual(image.getpixel((16, 16))[:3], (0, 0, 0))
                    else:
                        self.assertEqual([field for field, _ in files], ["image"])
                        self.assertEqual(image.getpixel((16, 16)), (200, 100, 50, 128))

    def test_preview_reuses_approved_drawing_without_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(generate_previews, "OUT_DIR", Path(temporary)), patch.object(generate_previews.requests, "post") as post:
                _, path, error = generate_previews.generate(MATERIALS["childlike_sketch"], force=True)
                self.assertIsNone(error)
                image = Image.open(path)
                self.assertEqual(image.size, (256, 256))
                self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
                post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
