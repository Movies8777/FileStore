import os
import urllib.parse
import requests
from aiohttp import web
from database import db

routes = web.RouteTableDef()


def get_browser(request):
    ua = request.headers.get("User-Agent", "Unknown")
    if "Telegram" in ua:
        return "Telegram In-App Browser"
    if "Chrome" in ua:
        return "Chrome"
    if "Safari" in ua:
        return "Safari"
    if "Firefox" in ua:
        return "Firefox"
    return "Other"


def create_shortlink(long_url):
    api_key = os.getenv("SHORTLINK_API")
    domain = os.getenv("SHORTLINK_URL")

    if not api_key or not domain:
        return None, "Shortlink ENV missing"

    encoded = urllib.parse.quote(long_url, safe="")
    api_url = f"https://{domain}/api?api={api_key}&url={encoded}"

    try:
        res = requests.get(api_url, timeout=10).json()
        if res.get("status") == "error":
            return None, res.get("message")
        return res.get("shortenedUrl"), None
    except Exception as e:
        return None, str(e)


@routes.get("/link/{user_id}/{page_token}/verify")
async def verify_page(request):
    user_id = int(request.match_info["user_id"])
    page_token = request.match_info["page_token"]

    browser = get_browser(request)
    verify_data = await db.get_verify_status(user_id)

    debug = {
        "user_id": user_id,
        "page_token_from_url": page_token,
        "page_token_in_db": verify_data.get("page_token"),
        "verify_token": verify_data.get("verify_token"),
        "is_verified": verify_data.get("is_verified"),
        "verified_time": verify_data.get("verified_time"),
        "browser": browser
    }

    # ❌ Invalid / expired
    if verify_data.get("page_token") != page_token:
        return web.json_response(
            {**debug, "error": "Invalid or expired page token"},
            status=403
        )

    # ✅ Already verified → redirect directly
    if verify_data.get("is_verified"):
        return web.HTTPFound(verify_data.get("link"))

    bot_username = os.getenv("BOT_USERNAME")
    telegram_link = f"https://t.me/{bot_username}?start=verify_{verify_data['verify_token']}"

    short_url, err = create_shortlink(telegram_link)
    if err:
        return web.json_response({**debug, "shortlink_error": err}, status=500)

    # Save link
    await db.update_verify_status(
        user_id,
        verify_token=verify_data["verify_token"],
        page_token=page_token,
        link=short_url,
        is_verified=False,
        verified_time=0
    )

    # ✅ Plain white page + auto redirect
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Verification</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="2;url={short_url}">
        <style>
            body {{
                background:#fff;
                font-family:Arial;
                text-align:center;
                margin-top:60px;
            }}
        </style>
    </head>
    <body>
        <h3>Redirecting to verification…</h3>
        <p>If not redirected, <a href="{short_url}">click here</a></p>
        <hr>
        <pre>{debug}</pre>
    </body>
    </html>
    """

    return web.Response(text=html, content_type="text/html")
