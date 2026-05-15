"""Generate one preview sphere per material via gpt-image-1.5.

Outputs PNGs to static/previews/{material_id}.png (256x256 RGBA, native alpha).

Runs ~5 generations concurrently. Total time roughly 60-90 seconds for 10 materials.

Usage:
    python generate_previews.py            # generate missing
    python generate_previews.py --force    # regenerate all
"""
from __future__ import annotations

import argparse
import base64
import io
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image

from materials import MATERIALS

load_dotenv(".env", override=True)
ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]
KEY = os.environ["AZURE_OPENAI_API_KEY"]
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

OUT_DIR = Path(__file__).resolve().parent / "static" / "previews"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_prompt(m: dict) -> str:
    return (
        "Material preview swatch for a design tool UI — the swatch will be composited on any UI "
        "background, so the orb must be perfectly cut out with NO shadow anywhere.\n"
        f"Subject: A perfectly smooth 3D rendered orb (sphere) made of {m['material_phrase']}. "
        f"{m['details']}.\n"
        "Composition: the orb is centered, occupying about 70% of the frame, "
        "square framing, head-on viewpoint, no tilt.\n"
        "Lighting: even diffuse studio lighting that reveals the material from multiple sides. "
        "Form-revealing self-shading IS allowed on the orb itself. "
        "Specular highlights on the orb surface are allowed.\n"
        "Background / surroundings: COMPLETELY EMPTY, FULLY TRANSPARENT VOID. "
        "There is no floor, no plane, no ground, no surface beneath, behind or around the orb. "
        "The orb floats in pure transparent space.\n"
        "Shadow constraints — STRICTLY ENFORCED:\n"
        "  - NO drop shadow under or behind the orb.\n"
        "  - NO cast shadow on any surface.\n"
        "  - NO contact shadow at the base.\n"
        "  - NO soft halo, soft glow or grey fade in surrounding pixels (unless the material itself glows).\n"
        "  - Every pixel that is not part of the orb material must be 100% transparent (alpha 0), "
        "not grey, not faded, not soft-shadowed.\n"
        "Other constraints: no text, no labels, no decorations, no other objects, single orb only."
    )


def generate(m: dict, force: bool) -> tuple[str, Path | None, str | None]:
    out = OUT_DIR / f"{m['id']}.png"
    if out.exists() and not force:
        return m["id"], out, "skipped (exists)"

    url = f"{ENDPOINT}/openai/deployments/{DEPLOYMENT}/images/generations?api-version={API_VERSION}"
    payload = {
        "prompt": build_prompt(m),
        "size": "1024x1024",
        "n": 1,
        "quality": "medium",
        "output_format": "png",
        "background": "transparent",
    }
    headers = {"api-key": KEY, "Content-Type": "application/json"}

    for attempt in range(5):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=180)
        except requests.RequestException as e:
            if attempt == 4:
                return m["id"], None, f"network: {e}"
            time.sleep(min(2 ** attempt, 30))
            continue
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", "6"))
            print(f"[{m['id']}] 429, wait {wait}s ({attempt+1}/5)", file=sys.stderr)
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            return m["id"], None, f"HTTP {resp.status_code}: {resp.text[:300]}"
        raw = base64.b64decode(resp.json()["data"][0]["b64_json"])
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        # 256x256 is plenty for the material grid card; saves bandwidth + paint cost
        img = img.resize((256, 256), Image.LANCZOS)
        img.save(out, format="PNG", optimize=True)
        return m["id"], out, None
    return m["id"], None, "exhausted retries"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Regenerate even if file exists")
    args = ap.parse_args()

    materials = list(MATERIALS.values())
    print(f"Generating {len(materials)} material previews -> {OUT_DIR}")
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(generate, m, args.force): m["id"] for m in materials}
        for f in as_completed(futures):
            mid, path, msg = f.result()
            if path and msg and msg.startswith("skipped"):
                print(f"  ··  {mid:12s}  {msg}")
            elif path:
                size_kb = path.stat().st_size / 1024
                print(f"  OK  {mid:12s}  {size_kb:.0f} KB  -> {path.name}")
            else:
                print(f"  XX  {mid:12s}  {msg}", file=sys.stderr)
    print(f"Done in {time.monotonic()-t0:.1f}s")


if __name__ == "__main__":
    main()
