from aiohttp import web
import os
import aiohttp
import urllib.parse
from datetime import datetime, timedelta

from database.database import db

routes = web.RouteTableDef()

# ──────────────── ENV ────────────────
BOT_USERNAME = os.getenv("BOT_USERNAME")       # without @
SHORTLINK_API = os.getenv("SHORTLINK_API")
SHORTLINK_URL = os.getenv("SHORTLINK_URL")
KOYEB_URL = os.getenv("KOYEB_URL")

# ──────────────── UTILS ────────────────

async def resolve_shortlink(url):
    """Resolve shortlink server-side (anti-bypass)"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True, timeout=10) as r:
                return str(r.url)
    except:
        return url


def error_page(message, status=400):
    html = f"""
    <html>
    <head><title>Error</title></head>
    <body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:Arial">
        <div style="text-align:center">
            <h3>{message}</h3>
            <p>Please try again later</p>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html", status=status)

# ──────────────── ROOT ────────────────

@routes.get("/")
async def root(_):
    return web.json_response("Movies8777 FileStore")

# ──────────────── TELEGRAM VERIFY ────────────────

@routes.get("/telegram/{user_id}/{page_token}")
async def telegram_verify(request):
    user_id = int(request.match_info["user_id"])
    page_token = request.match_info["page_token"]

    user = await db.get_verify_status(user_id)
    if not user or user.get("page_token") != page_token:
        return error_page("Invalid or expired verification link")

    if user.get("is_verified"):
        return verified_page()

    telegram_link = f"https://t.me/{BOT_USERNAME}?start=verify_{user['verify_token']}"
    encoded = urllib.parse.quote(telegram_link, safe="")

    api = f"https://{SHORTLINK_URL}/api?api={SHORTLINK_API}&url={encoded}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api) as r:
            data = await r.json()

    shortlink = data.get("shortenedUrl")
    if not shortlink:
        return error_page("Verification service unavailable")

    await db.create_redirect(user["redirect_id"], shortlink, user_id)

    return web.HTTPFound(f"/redirect?id={user['redirect_id']}")

# ──────────────── REDIRECT GATEWAY ────────────────

@routes.get("/redirect")
async def redirect_handler(request):
    redirect_id = request.query.get("id")
    if not redirect_id:
        return error_page("Invalid request")

    data = await db.get_redirect_full(redirect_id)
    if not data:
        return error_page("Link expired", 404)

    user_id = data["user_id"]
    created = data["created_at"]

    verify = await db.get_verify_status(user_id)
    is_verified = verify and verify.get("is_verified")

    # Expiry for unverified users
    if not is_verified and datetime.utcnow() - created > timedelta(minutes=2):
        return error_page("Verification link expired", 404)

    if is_verified:
        return verified_page()

    final_url = await resolve_shortlink(data["shortlink"])

    await db.mark_redirect_visited(redirect_id)

    return redirect_loader(final_url)

# ──────────────── VERIFIED PAGE ────────────────

def verified_page():
    return web.Response(
        text="""
        <html><body style="background:#000;color:#0f0;display:flex;align-items:center;justify-content:center;height:100vh">
        <div style="text-align:center">
            <h1>✔ Verified</h1>
            <p>You already have access</p>
            <a href="https://t.me/Spicylinebun">Back to Bot</a>
        </div>
        </body></html>
        """,
        content_type="text/html"
    )

# ──────────────── LOADER PAGE ────────────────

def redirect_loader(url):
    return web.Response(
        text=f"""
        <html>
        <head>
            <meta http-equiv="refresh" content="2;url={url}">
            <title>Redirecting</title>
        </head>
        <body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:Arial">
            <div>
                <h2>Redirecting...</h2>
                <p>Please wait</p>
            </div>
        </body>
        </html>
        """,
        content_type="text/html"
    )
