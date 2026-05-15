"""Assets Generator backend with async job queue.

Endpoints:
  GET    /api/materials                -> list of material presets
  GET    /api/icons?q=...&limit=48     -> Iconify search proxy
  GET    /api/icon-svg?prefix=&name=   -> Iconify SVG proxy
  POST   /api/jobs (multipart)         -> enqueue a generation job, returns job_id
  GET    /api/jobs                     -> list all jobs (summary)
  GET    /api/jobs/{id}                -> job detail (status, metadata)
  GET    /api/jobs/{id}/result.png     -> PNG bytes when status=succeeded
  DELETE /api/jobs/{id}                -> cancel (if queued) or remove
  POST   /api/jobs/clear-completed     -> remove all succeeded/failed/cancelled jobs
  GET    /api/config                   -> { concurrency_limit }

Generation runs via a pool of worker coroutines. Each worker pops a job from
an asyncio.Queue and offloads the blocking Azure call to a thread.
Concurrency is capped by MAX_CONCURRENCY (defaults to 5; gpt-image-1.5 allows 60 RPM).
"""
from __future__ import annotations

import asyncio
import base64
import io
import os
import secrets
import sys
import time
import urllib.parse
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from starlette.middleware.sessions import SessionMiddleware

from materials import MATERIALS, build_prompt

# ---------------- Config ----------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

AZURE_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
AZURE_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
AZURE_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
MAX_CONCURRENCY = int(os.environ.get("MAX_CONCURRENCY", "5"))

# ---- Auth config
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
# Comma-separated allowlist; lowercased on load.
ALLOWED_EMAILS = {e.strip().lower() for e in os.environ.get("ALLOWED_EMAILS", "").split(",") if e.strip()}
# Public URL the app is served on — used to build the OAuth redirect URI.
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
# Signed-cookie secret. In dev we auto-generate; in prod, set explicitly.
SESSION_SECRET = os.environ.get("SESSION_SECRET", "").strip() or secrets.token_urlsafe(48)
# Auth is OFF when no client id is set (dev fallback). In prod the env should always set it.
AUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and ALLOWED_EMAILS)

if not all([AZURE_ENDPOINT, AZURE_DEPLOYMENT, AZURE_API_KEY]):
    print("ERROR: Azure OpenAI config incomplete in .env", file=sys.stderr)
    sys.exit(1)

if AUTH_ENABLED:
    if not PUBLIC_URL:
        print("WARN: AUTH_ENABLED but PUBLIC_URL missing — OAuth redirect URI will be relative.",
              file=sys.stderr)
    print(f"[auth] Google OAuth enabled, allowlist: {sorted(ALLOWED_EMAILS)}", file=sys.stderr)
else:
    print("[auth] DISABLED (no GOOGLE_CLIENT_ID/SECRET/ALLOWED_EMAILS set) — app is open", file=sys.stderr)

ICONIFY_BASE = "https://api.iconify.design"

# gpt-image-1.5 accepts these square/landscape/portrait sizes. We always generate
# at the closest matching size to the target ratio, then resize to user pixels.
GENERATION_SIZES = {
    "1:1": (1024, 1024),
    "3:2": (1536, 1024),
    "2:3": (1024, 1536),
}

# ---------------- Job store (in-memory) ----------------
# Single-process FastAPI -> a plain dict is fine. Jobs survive only as long as
# the server process runs.
JOBS: dict[str, dict[str, Any]] = {}
job_queue: asyncio.Queue[str] = asyncio.Queue()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def job_summary(j: dict) -> dict:
    """Strip heavy fields for list endpoints."""
    return {
        "id": j["id"],
        "status": j["status"],
        "created_at": j["created_at"],
        "started_at": j.get("started_at"),
        "finished_at": j.get("finished_at"),
        "params": j["params"],
        "icon_svg_url": j["icon_svg_url"],
        "error": j.get("error"),
        "has_result": "result_png" in j,
        "elapsed_ms": j.get("elapsed_ms"),
    }


def queue_position(job_id: str) -> int:
    """1-based position among queued jobs. 0 if not queued anymore."""
    if JOBS.get(job_id, {}).get("status") != "queued":
        return 0
    queued = [j for j in JOBS.values() if j["status"] == "queued"]
    queued.sort(key=lambda j: j["created_at"])
    for i, j in enumerate(queued):
        if j["id"] == job_id:
            return i + 1
    return 0


# ---------------- Worker loop ----------------
async def worker_loop(idx: int) -> None:
    print(f"[worker-{idx}] started", file=sys.stderr)
    while True:
        try:
            job_id = await job_queue.get()
        except asyncio.CancelledError:
            print(f"[worker-{idx}] cancelled", file=sys.stderr)
            return
        try:
            await _process(job_id)
        except Exception as e:
            print(f"[worker-{idx}] crashed on {job_id}: {e}", file=sys.stderr)
            j = JOBS.get(job_id)
            if j and j["status"] == "in_progress":
                j["status"] = "failed"
                j["error"] = f"Worker crash: {e}"
                j["finished_at"] = now_iso()
        finally:
            job_queue.task_done()


async def _process(job_id: str) -> None:
    job = JOBS.get(job_id)
    if not job:
        return
    if job["status"] != "queued":  # cancelled while in queue, or stale
        return
    job["status"] = "in_progress"
    job["started_at"] = now_iso()
    t0 = time.monotonic()
    try:
        result_png = await asyncio.to_thread(_do_generation, job)
        job["result_png"] = result_png
        job["status"] = "succeeded"
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        job["finished_at"] = now_iso()
        job["elapsed_ms"] = int((time.monotonic() - t0) * 1000)


def _do_generation(job: dict) -> bytes:
    """Synchronous Azure call (runs in a worker thread). Returns final PNG bytes."""
    params = job["params"]
    img_bytes = job["input_png"]

    gen_w, gen_h = GENERATION_SIZES[params["ratio"]]
    prompt = build_prompt(params["material_id"])

    url = (
        f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}"
        f"/images/edits?api-version={AZURE_API_VERSION}"
    )
    files = [("image", ("icon.png", img_bytes, "image/png"))]
    data = {
        "prompt": prompt,
        "size": f"{gen_w}x{gen_h}",
        "quality": params["quality"],
        "n": "1",
        "output_format": "png",
        "background": "transparent",  # gpt-image-1.5: native alpha, no post-processing needed
    }
    headers = {"api-key": AZURE_API_KEY}

    resp = _azure_post_with_retry(url, headers, data, files)
    if resp.status_code != 200:
        snippet = resp.text[:500]
        raise RuntimeError(f"Azure {resp.status_code}: {snippet}")

    result = resp.json()
    raw = base64.b64decode(result["data"][0]["b64_json"])

    # Resize to the user's target dimensions while preserving alpha.
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    img = img.resize((params["width"], params["height"]), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _azure_post_with_retry(url: str, headers: dict, data: dict, files: list,
                            max_attempts: int = 5) -> requests.Response:
    """POST with retry on 429 (rate limit) and 5xx, honoring Retry-After."""
    last: requests.Response | None = None
    for attempt in range(max_attempts):
        try:
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=180)
        except requests.RequestException as e:
            if attempt == max_attempts - 1:
                raise RuntimeError(f"Network error to Azure: {e}")
            time.sleep(min(2 ** attempt, 30))
            continue
        last = resp
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", "6"))
            print(f"[azure] 429, waiting {wait}s ({attempt+1}/{max_attempts})", file=sys.stderr)
            if attempt == max_attempts - 1:
                return resp
            time.sleep(wait)
            continue
        if 500 <= resp.status_code < 600 and attempt < max_attempts - 1:
            time.sleep(min(2 ** attempt, 30))
            continue
        return resp
    return last  # type: ignore[return-value]


# ---------------- FastAPI lifespan + app ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    workers = [asyncio.create_task(worker_loop(i)) for i in range(MAX_CONCURRENCY)]
    print(f"[lifespan] started {MAX_CONCURRENCY} workers", file=sys.stderr)
    try:
        yield
    finally:
        for w in workers:
            w.cancel()
        for w in workers:
            try:
                await w
            except (asyncio.CancelledError, Exception):
                pass


app = FastAPI(title="Assets Generator", lifespan=lifespan)


# ---------------- Auth helpers ----------------
# Paths that never require authentication (the login flow itself + static assets
# that need to load on the login page).
_PUBLIC_PREFIXES = (
    "/auth/", "/login.html", "/style.css", "/app.js",
    "/previews/",  # OK to leak — they're sphere swatches
    "/favicon", "/openapi.json", "/docs", "/redoc",
)
_PUBLIC_EXACT = {"/api/me", "/api/config"}


def _is_public_path(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    return any(path.startswith(p) for p in _PUBLIC_PREFIXES)


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    if not AUTH_ENABLED:
        return await call_next(request)
    path = request.url.path
    if _is_public_path(path):
        return await call_next(request)

    email = request.session.get("user_email")
    authorized = bool(email) and email in ALLOWED_EMAILS

    # API: return 401 JSON so the frontend can react.
    if path.startswith("/api/"):
        if not authorized:
            return JSONResponse({"detail": "auth required"}, status_code=401)
        return await call_next(request)

    # Page navigation: redirect to login screen.
    if not authorized:
        return RedirectResponse("/login.html", status_code=302)
    return await call_next(request)


def _redirect_uri() -> str:
    base = PUBLIC_URL or ""
    return f"{base}/auth/google/callback"


@app.get("/auth/google/login")
def google_login(request: Request):
    if not AUTH_ENABLED:
        raise HTTPException(503, "auth not configured")
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url, status_code=302)


@app.get("/auth/google/callback")
def google_callback(request: Request, code: str | None = None,
                     state: str | None = None, error: str | None = None):
    if not AUTH_ENABLED:
        raise HTTPException(503, "auth not configured")
    if error:
        return RedirectResponse(f"/login.html?error={urllib.parse.quote(error)}", status_code=302)
    expected = request.session.pop("oauth_state", None)
    if not code or not state or state != expected:
        return RedirectResponse("/login.html?error=invalid_state", status_code=302)
    try:
        tok = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        tok.raise_for_status()
        access_token = tok.json().get("access_token")
        if not access_token:
            raise RuntimeError("no access_token in token response")
        info = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        info.raise_for_status()
        user = info.json()
    except (requests.RequestException, RuntimeError, ValueError) as e:
        print(f"[auth] OAuth exchange failed: {e}", file=sys.stderr)
        return RedirectResponse("/login.html?error=token_exchange", status_code=302)

    email = (user.get("email") or "").lower()
    verified = bool(user.get("email_verified"))
    if not email or not verified:
        return RedirectResponse("/login.html?error=unverified", status_code=302)
    if email not in ALLOWED_EMAILS:
        # Tell the user which account was tried so they can switch.
        q = urllib.parse.urlencode({"error": "unauthorized", "email": email})
        return RedirectResponse(f"/login.html?{q}", status_code=302)

    request.session["user_email"] = email
    request.session["user_name"] = user.get("name", "")
    request.session["user_picture"] = user.get("picture", "")
    return RedirectResponse("/", status_code=302)


@app.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    if not AUTH_ENABLED:
        return {"authenticated": True, "email": "anonymous", "auth_enabled": False}
    email = request.session.get("user_email")
    if not email or email not in ALLOWED_EMAILS:
        return JSONResponse({"authenticated": False, "auth_enabled": True}, status_code=401)
    return {
        "authenticated": True,
        "auth_enabled": True,
        "email": email,
        "name": request.session.get("user_name", ""),
        "picture": request.session.get("user_picture", ""),
    }


# Add SessionMiddleware AFTER the auth_gate decorator so it ends up at the outer
# layer of the middleware stack (last registered = first to wrap = first to
# execute on incoming). Otherwise auth_gate runs before SessionMiddleware has
# populated request.session and we hit AssertionError.
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    https_only=PUBLIC_URL.startswith("https://"),
    same_site="lax",
    max_age=14 * 24 * 3600,  # 14 days
)


# ---------------- Read-only endpoints ----------------
@app.get("/api/config")
def get_config():
    return {
        "concurrency_limit": MAX_CONCURRENCY,
        "deployment": AZURE_DEPLOYMENT,
    }


@app.get("/api/materials")
def list_materials():
    previews_dir = BASE_DIR / "static" / "previews"
    return [
        {
            "id": m["id"],
            "label": m["label"],
            "emoji": m["emoji"],
            "swatch": m["swatch"],
            "description": m["description"],
            # Previews generated via generate_previews.py; gracefully degrade if missing.
            "preview_url": f"/previews/{m['id']}.png" if (previews_dir / f"{m['id']}.png").exists() else None,
        }
        for m in MATERIALS.values()
    ]


@app.get("/api/icons")
def search_icons(q: str, limit: int = 48):
    q = q.strip()
    if not q:
        return {"icons": [], "total": 0}
    try:
        resp = requests.get(
            f"{ICONIFY_BASE}/search",
            params={"query": q, "limit": min(max(limit, 1), 96)},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Iconify search failed: {e}")
    icons = []
    for full in data.get("icons", []):
        if ":" not in full:
            continue
        prefix, name = full.split(":", 1)
        icons.append({
            "id": full,
            "prefix": prefix,
            "name": name,
            "svg_url": f"{ICONIFY_BASE}/{prefix}/{name}.svg",
        })
    return {"icons": icons, "total": data.get("total", len(icons))}


def _safe_ident(s: str) -> bool:
    return bool(s) and len(s) <= 60 and all(c.isalnum() or c in "-_" for c in s)


@app.get("/api/icon-svg")
def get_icon_svg(prefix: str, name: str):
    if not (_safe_ident(prefix) and _safe_ident(name)):
        raise HTTPException(status_code=400, detail="Invalid icon identifier")
    try:
        resp = requests.get(f"{ICONIFY_BASE}/{prefix}/{name}.svg", timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Iconify svg failed: {e}")
    return Response(content=resp.text, media_type="image/svg+xml")


# ---------------- Job endpoints ----------------
@app.post("/api/jobs")
async def create_job(
    image: UploadFile = File(...),
    material_id: str = Form(...),
    ratio: str = Form("1:1"),
    width: int = Form(512),
    height: int = Form(512),
    quality: str = Form("medium"),
    icon_id: str = Form(""),
    icon_label: str = Form(""),
    icon_svg_url: str = Form(""),
):
    # ---- validation
    if material_id not in MATERIALS:
        raise HTTPException(status_code=400, detail=f"Unknown material: {material_id}")
    if ratio not in GENERATION_SIZES:
        raise HTTPException(status_code=400, detail=f"Unknown ratio: {ratio}")
    if quality not in ("low", "medium", "high"):
        raise HTTPException(status_code=400, detail="quality must be low|medium|high")
    if not (64 <= width <= 4096 and 64 <= height <= 4096):
        raise HTTPException(status_code=400, detail="size out of range (64..4096)")

    img_bytes = await image.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="Empty image upload")
    if len(img_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (>8 MB)")

    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "created_at": now_iso(),
        "input_png": img_bytes,
        "icon_svg_url": icon_svg_url,
        "params": {
            "material_id": material_id,
            "material_label": MATERIALS[material_id]["label"],
            "icon_id": icon_id,
            "icon_label": icon_label,
            "ratio": ratio,
            "width": width,
            "height": height,
            "quality": quality,
        },
    }
    await job_queue.put(job_id)
    return {
        "id": job_id,
        "status": "queued",
        "position": queue_position(job_id),
    }


@app.get("/api/jobs")
def list_jobs():
    items = [job_summary(j) for j in JOBS.values()]
    items.sort(key=lambda j: j["created_at"], reverse=True)
    return {
        "jobs": items,
        "in_flight": sum(1 for j in items if j["status"] in ("queued", "in_progress")),
        "completed": sum(1 for j in items if j["status"] == "succeeded"),
        "failed": sum(1 for j in items if j["status"] in ("failed", "cancelled")),
    }


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    j = JOBS.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_summary(j)


@app.get("/api/jobs/{job_id}/result.png")
def get_job_result(job_id: str):
    j = JOBS.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    if j["status"] != "succeeded" or "result_png" not in j:
        raise HTTPException(status_code=409, detail=f"Job not ready (status={j['status']})")
    return Response(
        content=j["result_png"],
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{j["params"]["icon_label"] or "asset"}-'
                                    f'{j["params"]["material_id"]}.png"',
            # don't cache while job is fresh — the server may delete it
            "Cache-Control": "no-store",
        },
    )


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    j = JOBS.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    # If it's queued, mark cancelled so the worker skips it when it dequeues.
    if j["status"] == "queued":
        j["status"] = "cancelled"
        j["finished_at"] = now_iso()
    # For terminal states, just remove from store.
    if j["status"] in ("succeeded", "failed", "cancelled"):
        JOBS.pop(job_id, None)
    # In-progress jobs cannot be aborted mid-flight (Azure call already inflight) —
    # they will complete and the user can delete them afterward.
    return {"ok": True, "status": j["status"]}


@app.post("/api/jobs/clear-completed")
def clear_completed():
    to_remove = [
        jid for jid, j in JOBS.items()
        if j["status"] in ("succeeded", "failed", "cancelled")
    ]
    for jid in to_remove:
        JOBS.pop(jid, None)
    return {"removed": len(to_remove)}


# ---------------- Static frontend ----------------
app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static")
