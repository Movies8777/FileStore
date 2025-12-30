from aiohttp import web
import os
import urllib.parse
import aiohttp
from datetime import datetime

from database.database import db

routes = web.RouteTableDef()

# ──────────────── ENV ────────────────
BOT_USERNAME = os.getenv("BOT_USERNAME")       # without @
SHORTLINK_URL = os.getenv("SHORTLINK_URL")     # domain only
SHORTLINK_API = os.getenv("SHORTLINK_API")     # api key


# ──────────────── ERROR PAGE ────────────────
def error_page(message, status=400):
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <title>Error</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:Arial">
  <div style="text-align:center">
    <h3>{message}</h3>
    <p>Please try again later</p>
  </div>
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html", status=status)


# ──────────────── MAIN TELEGRAM VERIFY ROUTE ────────────────
@routes.get("/telegram/{user_id}/{page_token}", allow_head=True)
async def telegram_verify(request):
    try:
        # 1️⃣ PARAMS
        user_id = int(request.match_info["user_id"])
        page_token = request.match_info["page_token"]

        if not BOT_USERNAME or not SHORTLINK_URL or not SHORTLINK_API:
            return error_page("Service unavailable")

        # 2️⃣ DB CHECK (SAME AS YOUR FILE)
        user = await db.get_verify_status(user_id)
        if not user:
            return error_page("Invalid verification link")

        if user.get("page_token") != page_token:
            return error_page("Link expired or invalid")

        if not user.get("verify_token"):
            return error_page("Verification unavailable")

        # 3️⃣ TELEGRAM DEEP LINK (UNCHANGED)
        telegram_link = (
            f"https://t.me/{BOT_USERNAME}"
            f"?start=verify_{user['verify_token']}"
        )

        # 4️⃣ SHORTLINK CREATE (UNCHANGED METHOD)
        encoded_url = urllib.parse.quote(telegram_link, safe="")
        api_url = (
            f"https://{SHORTLINK_URL}/api"
            f"?api={SHORTLINK_API}"
            f"&url={encoded_url}"
        )

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:
            async with session.get(api_url) as resp:
                if resp.status != 200:
                    return error_page("Redirection failed")

                data = await resp.json()

        short_url = data.get("shortenedUrl")
        if not short_url:
            return error_page("Redirection failed")

        # 5️⃣ OPTIONAL: LOG VISIT (SAFE ADDITION)
        try:
            await db.log_verify_visit(
                user_id=user_id,
                ip=request.remote,
                time=datetime.utcnow()
            )
        except:
            pass

        # 6️⃣ SAME LOADER + META REFRESH (WORKING)
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
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
</head>

<body>
  <div class="card">
    <div class="loader"></div>
    <h2>Redirecting...</h2>
    <p>Please wait while we take you to Telegram</p>
  </div>
</body>
</html>
"""
        return web.Response(text=html, content_type="text/html")

    except Exception:
        return error_page("Something went wrong")
