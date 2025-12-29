from aiohttp import web
import os
import urllib.parse
import aiohttp

from database.database import db

routes = web.RouteTableDef()

# ENV VARIABLES
BOT_USERNAME = os.getenv("BOT_USERNAME")       # without @
SHORT_URL = os.getenv("SHORTLINK_URL")
INSHORT_API_KEY = os.getenv("SHORTLINK_API")


# =========================
# 🔍 BROWSER DETECTION
# =========================
def detect_browser(request):
    ua = request.headers.get("User-Agent", "").lower()

    browser = "Unknown"
    if "chrome" in ua and "edg" not in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "edg" in ua:
        browser = "Edge"
    elif "opera" in ua or "opr" in ua:
        browser = "Opera"

    platform = "Desktop"
    if "android" in ua:
        platform = "Android"
    elif "iphone" in ua or "ipad" in ua:
        platform = "iOS"

    return browser, platform, ua


# =========================
# 🚀 MAIN ROUTE
# =========================
@routes.get("/telegram/{user_id}/{page_token}", allow_head=True)
async def telegram_verify(request):
    try:
        # 1️⃣ PARAMS
        user_id = int(request.match_info["user_id"])
        page_token = request.match_info["page_token"]

        # debug flag (?debug=1)
        debug = request.query.get("debug") == "1"

        if not BOT_USERNAME:
            return error_page("Service unavailable")

        # 🔍 Browser check
        browser, platform, ua = detect_browser(request)

        # Console log (Render / Koyeb logs)
        print(
            f"[VERIFY] user={user_id} | browser={browser} | platform={platform} | ua={ua}"
        )

        # 2️⃣ DATABASE CHECK
        user = await db.get_verify_status(user_id)
        if not user:
            return error_page("Invalid verification link")

        if user.get("page_token") != page_token:
            return error_page("Link expired or invalid")

        if not user.get("verify_token"):
            return error_page("Verification unavailable")

        # 3️⃣ TELEGRAM LINK
        telegram_link = (
            f"https://t.me/{BOT_USERNAME}"
            f"?start=verify_{user['verify_token']}"
        )

        # 4️⃣ SHORT LINK
        if not INSHORT_API_KEY or not SHORT_URL:
            return error_page("Service unavailable")

        encoded_url = urllib.parse.quote(telegram_link, safe="")
        api_url = (
            f"https://{SHORT_URL}/api"
            f"?api={INSHORT_API_KEY}"
            f"&url={encoded_url}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=15) as resp:
                data = await resp.json()

        short_url = data.get("shortenedUrl")
        if not short_url:
            return error_page("Redirection failed")

        # 🧪 DEBUG HTML
        debug_html = ""
        if debug:
            debug_html = f"""
            <p style="margin-top:14px;font-size:13px;color:#475569">
              <b>Debug Info</b><br>
              Browser: {browser}<br>
              Platform: {platform}
            </p>
            """

        # 5️⃣ REDIRECT PAGE
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Redirecting...</title>
  <meta http-equiv="refresh" content="2;url={short_url}">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <style>
    body {{
      margin: 0;
      height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: radial-gradient(circle at top, #cfe3ff 0%, #e8ddff 45%, #f3e8ff 100%);
    }}

    .card {{
      width: 88%;
      max-width: 420px;
      background: rgba(255,255,255,0.88);
      backdrop-filter: blur(16px);
      border-radius: 22px;
      padding: 34px 26px;
      text-align: center;
      box-shadow: 0 30px 60px rgba(0,0,0,0.12);
      animation: slideUp 0.6s ease-out;
    }}

    .loader {{
      width: 44px;
      height: 44px;
      margin: 0 auto 18px;
      border-radius: 50%;
      border: 4px solid #dbeafe;
      border-top-color: #3b82f6;
      animation: spin 1s linear infinite;
    }}

    h2 {{
      margin: 0;
      font-size: 22px;
      font-weight: 600;
      color: #0f172a;
    }}

    p {{
      margin-top: 10px;
      font-size: 15px;
      line-height: 1.5;
      color: #64748b;
    }}

    @keyframes spin {{
      to {{ transform: rotate(360deg); }}
    }}

    @keyframes slideUp {{
      from {{
        opacity: 0;
        transform: translateY(20px);
      }}
      to {{
        opacity: 1;
        transform: translateY(0);
      }}
    }}
  </style>
</head>

<body>
  <div class="card">
    <div class="loader"></div>
    <h2>Redirecting...</h2>
    <p>Please wait while we take you to your destination.</p>
    {debug_html}
  </div>
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
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <title>Error</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      background:#ffffff;
      font-family:Arial;
      display:flex;
      justify-content:center;
      align-items:center;
      height:100vh;
      color:#0f172a;
    }}
    .box {{
      text-align:center;
      padding:30px;
      border-radius:16px;
      box-shadow:0 10px 30px rgba(0,0,0,0.08);
    }}
    h3 {{ margin-bottom:8px; }}
    p {{ color:#64748b; }}
  </style>
</head>
<body>
  <div class="box">
    <h3>{message}</h3>
    <p>Please try again later</p>
  </div>
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html", status=400)


# =========================
# 🔗 ROUTE SETUP
# =========================
def setup_routes(app):
    app.add_routes(routes)
