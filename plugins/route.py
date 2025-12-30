from aiohttp import web
import os
import urllib.parse
import aiohttp
from database.database import db

routes = web.RouteTableDef()

BOT_USERNAME = os.getenv("BOT_USERNAME")
SHORTLINK_API = os.getenv("SHORTLINK_API")
SHORTLINK_URL = os.getenv("SHORTLINK_URL")


# =========================
# SHORTLINK CREATOR
# =========================
async def create_shortlink(url):
    if not SHORTLINK_API or not SHORTLINK_URL:
        return url

    try:
        encoded = urllib.parse.quote(url, safe="")
        api = f"https://{SHORTLINK_URL}/api?api={SHORTLINK_API}&url={encoded}"

        async with aiohttp.ClientSession() as session:
            async with session.get(api, timeout=10) as resp:
                data = await resp.json()
                return data.get("shortenedUrl", url)

    except Exception as e:
        print("[SHORTLINK ERROR]", e)
        return url


# =========================
# MAIN TELEGRAM ROUTE
# =========================
@routes.get("/telegram/{user_id}/{page_token}")
async def telegram_handler(request):
    user_id = int(request.match_info["user_id"])
    page_token = request.match_info["page_token"]
    ext = request.query.get("ext")  # external browser flag

    user = await db.get_verify_status(user_id)
    if not user or user.get("page_token") != page_token:
        return error_page("Invalid or expired link")

    verify_url = f"https://t.me/{BOT_USERNAME}?start=verify_{user['verify_token']}"

    # =========================
    # EXTERNAL BROWSER → CREATE SHORTLINK
    # =========================
    if ext == "1":
        shortlink = await create_shortlink(verify_url)
        raise web.HTTPFound(shortlink)

    # =========================
    # TELEGRAM IN-APP DETECTION (STACKOVERFLOW METHOD)
    # =========================
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Redirecting…</title>
</head>
<body style="font-family:Arial;text-align:center;margin-top:40px">
<p>Opening secure browser…</p>

<script>
// StackOverflow recommended detection
function isTelegramInApp() {{
    return (
        typeof window.TelegramWebviewProxy !== "undefined" ||
        typeof window.Telegram !== "undefined" ||
        typeof window.TelegramWebApp !== "undefined" ||
        navigator.userAgent.toLowerCase().includes("telegram")
    );
}}

const externalUrl =
    window.location.origin +
    "/telegram/{user_id}/{page_token}?ext=1";

if (isTelegramInApp()) {{
    // Telegram In-App → force external browser
    window.location.href = externalUrl;
}} else {{
    // Already normal browser → allow shortlink creation
    window.location.href = externalUrl;
}}
</script>

</body>
</html>
"""

    return web.Response(text=html, content_type="text/html")


# =========================
# ERROR PAGE
# =========================
def error_page(msg):
    return web.Response(
        text=f"<h3 style='text-align:center;margin-top:40px'>{msg}</h3>",
        content_type="text/html",
        status=400
    )


def setup_routes(app):
    app.add_routes(routes)
