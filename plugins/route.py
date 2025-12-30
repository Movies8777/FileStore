from aiohttp import web
import os
import urllib.parse
import aiohttp

from database.database import db

routes = web.RouteTableDef()

# ENV
BOT_USERNAME = os.getenv("BOT_USERNAME")
SHORT_URL = os.getenv("SHORTLINK_URL")
SHORT_API = os.getenv("SHORTLINK_API")


# =========================
# 🔍 SERVER-SIDE BROWSER
# =========================
def detect_browser(request):
    ua = request.headers.get("User-Agent", "").lower()

    browser = "Unknown"
    platform = "Unknown"

    if "android" in ua:
        platform = "Android"
    elif "iphone" in ua or "ipad" in ua:
        platform = "iOS"
    elif "macintosh" in ua or "mac os x" in ua:
        platform = "macOS"
    elif "windows" in ua:
        platform = "Windows"
    elif "linux" in ua:
        platform = "Linux"
    else:
        platform = "Other"

    if "chrome" in ua and "edg" not in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "edg" in ua:
        browser = "Edge"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "opera" in ua or "opr" in ua:
        browser = "Opera"

    return browser, platform, ua


# =========================
# 🧪 FULL DEBUG ROUTE
# =========================
@routes.get("/telegram/{user_id}/{page_token}", allow_head=True)
async def telegram_debug(request):
    try:
        user_id = int(request.match_info["user_id"])
        page_token = request.match_info["page_token"]

        if not BOT_USERNAME:
            return error_page("BOT_USERNAME not set")

        # DB CHECK
        user = await db.get_verify_status(user_id)
        if not user or user.get("page_token") != page_token:
            return error_page("Invalid or expired link")

        verify_token = user.get("verify_token")

        # Telegram deep link
        telegram_link = f"https://t.me/{BOT_USERNAME}?start=verify_{verify_token}"

        # Shortlink (generated only)
        shortlink = "N/A"
        if SHORT_API and SHORT_URL:
            encoded = urllib.parse.quote(telegram_link, safe="")
            api_url = f"https://{SHORT_URL}/api?api={SHORT_API}&url={encoded}"
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=10) as resp:
                    data = await resp.json()
                    shortlink = data.get("shortenedUrl", "FAILED")

        # Browser detection (server)
        browser, platform, ua = detect_browser(request)

        print(
            f"[DEBUG] user={user_id} | platform={platform} | browser={browser}"
        )

        # =========================
        # DEBUG PAGE (WITH JS CHECK)
        # =========================
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Telegram Full Debug</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      margin: 0;
      padding: 20px;
      font-family: Arial, sans-serif;
      background: #f1f5f9;
    }}
    .card {{
      max-width: 760px;
      margin: auto;
      background: #ffffff;
      padding: 24px;
      border-radius: 14px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }}
    h2 {{ color:#0f172a; }}
    p {{ font-size:14px;color:#334155;margin:6px 0; }}
    code {{
      display:block;
      background:#0f172a;
      color:#e5e7eb;
      padding:10px;
      border-radius:10px;
      font-size:12px;
      word-break:break-all;
    }}
    .tag {{
      display:inline-block;
      padding:4px 8px;
      background:#e0e7ff;
      color:#1e3a8a;
      border-radius:8px;
      font-size:12px;
      margin-top:6px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h2>Telegram Verification – Full Debug</h2>

    <p><b>User ID:</b> {user_id}</p>
    <p><b>BOT Username:</b> @{BOT_USERNAME}</p>
    <p><b>Page Token:</b> {page_token}</p>
    <p><b>Verify Token:</b> {verify_token}</p>

    <hr>

    <p><b>Telegram Start Link:</b></p>
    <code>{telegram_link}</code>

    <p><b>Generated Shortlink:</b></p>
    <code>{shortlink}</code>

    <hr>

    <p><b>Platform (Server):</b> {platform}</p>
    <p><b>Browser (Server):</b> {browser}</p>

    <p class="tag">Server Debug</p>

    <hr>

    <p><b>User-Agent:</b></p>
    <code>{ua}</code>

    <hr>

    <p><b>Telegram In-App Detection (Client JS):</b></p>
    <p id="tg-status">Checking...</p>
    <p class="tag">Client Debug</p>
  </div>

  <script>
    let isTelegramWebview =
      typeof window.TelegramWebview !== "undefined" ||
      typeof window.TelegramWebviewProxy !== "undefined";

    document.getElementById("tg-status").innerHTML =
      isTelegramWebview ? "YES (Telegram In-App Browser)" : "NO (Normal Browser)";
  </script>
</body>
</html>
"""
        return web.Response(text=html, content_type="text/html")

    except Exception as e:
        print("[ERROR]", e)
        return error_page("Something went wrong")


# =========================
# ❌ ERROR PAGE
# =========================
def error_page(message):
    return web.Response(
        text=f"<h3 style='font-family:Arial;text-align:center;margin-top:40px'>{message}</h3>",
        content_type="text/html",
        status=400
    )


def setup_routes(app):
    app.add_routes(routes)
