from aiohttp import web
import aiohttp
import urllib.parse
import re
import os

# ==============================
# ENVIRONMENT VARIABLES
# ==============================
BOT_USERNAME = os.getenv("BOT_USERNAME")          # e.g. Movies8777Bot
SHORT_URL = os.getenv("SHORT_URL")                # e.g. softurl.in
INSHORT_API_KEY = os.getenv("INSHORT_API_KEY")    # API key

if not BOT_USERNAME or not SHORT_URL or not INSHORT_API_KEY:
    raise RuntimeError("Missing required environment variables")

# db must provide:
# await db.get_verify_status(user_id)
from database import db   # adjust if path differs

routes = web.RouteTableDef()

# ==============================
# BROWSER DETECTION (PBH STYLE)
# ==============================
def detect_browser(user_agent: str):
    if not user_agent:
        return "unknown"

    ua = user_agent.lower()

    if "telegram" in ua or "webview" in ua:
        return "telegram"
    if "chrome" in ua and "edg" not in ua:
        return "chrome"
    if "safari" in ua and "chrome" not in ua:
        return "safari"
    if "firefox" in ua:
        return "firefox"
    if "edg" in ua:
        return "edge"

    return "unknown"


# ==============================
# MAIN VERIFY ROUTE
# ==============================
@routes.get("/link/{masked_uid}/{page_token}/verify", allow_head=True)
async def verify_page(request):
    debug = {}

    try:
        # ─────────────────────────
        # 1️⃣ USER AGENT / BROWSER
        # ─────────────────────────
        user_agent = request.headers.get("User-Agent", "")
        browser = detect_browser(user_agent)

        debug["user_agent"] = user_agent
        debug["detected_browser"] = browser

        # ─────────────────────────
        # 2️⃣ EXTRACT USER ID
        # ─────────────────────────
        masked_uid = request.match_info["masked_uid"]
        page_token = request.match_info["page_token"]

        user_id = re.sub(r"\D", "", masked_uid)

        debug["masked_uid"] = masked_uid
        debug["user_id"] = user_id
        debug["page_token_from_url"] = page_token
        debug["bot_username"] = BOT_USERNAME

        if not user_id:
            debug["error"] = "Invalid user id"
            return web.json_response(debug, status=400)

        user_id = int(user_id)

        # ─────────────────────────
        # 3️⃣ TELEGRAM IN-APP BLOCK
        # ─────────────────────────
        if browser == "telegram":
            html = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Open in Browser</title>
<style>
body {{
  background:#ffffff;
  color:#000;
  font-family:Arial,sans-serif;
  display:flex;
  justify-content:center;
  align-items:center;
  height:100vh;
}}
.box {{
  text-align:center;
  max-width:420px;
}}
button {{
  background:#0088cc;
  color:#fff;
  border:none;
  padding:14px 22px;
  font-size:16px;
  border-radius:6px;
  cursor:pointer;
}}
pre {{
  margin-top:20px;
  font-size:12px;
  background:#f4f4f4;
  padding:10px;
  border:1px solid #ddd;
  text-align:left;
}}
</style>
</head>
<body>
<div class="box">
  <h2>Open in Browser</h2>
  <p>Please open this link in Chrome or Safari to continue.</p>
  <button onclick="window.open('{request.url}','_blank')">
    Open in Browser
  </button>
  <pre>{debug}</pre>
</div>
</body>
</html>
"""
            return web.Response(text=html, content_type="text/html")

        # ─────────────────────────
        # 4️⃣ DATABASE CHECK
        # ─────────────────────────
        user = await db.get_verify_status(user_id)

        if not user:
            debug["error"] = "User not found in database"
            return web.json_response(debug, status=404)

        debug["page_token_in_db"] = user.get("page_token")
        debug["verify_token"] = user.get("verify_token")
        debug["is_verified"] = user.get("is_verified")
        debug["verified_time"] = user.get("verified_time")

        if user.get("page_token") != page_token:
            debug["error"] = "Page token mismatch"
            return web.json_response(debug, status=403)

        # ─────────────────────────
        # 5️⃣ TELEGRAM DEEP LINK
        # ─────────────────────────
        telegram_link = (
            f"https://t.me/{BOT_USERNAME}"
            f"?start=verify_{user['verify_token']}"
        )

        debug["telegram_link"] = telegram_link

        # ─────────────────────────
        # 6️⃣ CREATE SHORTLINK
        # ─────────────────────────
        encoded_url = urllib.parse.quote(telegram_link, safe="")

        api_url = (
            f"https://{SHORT_URL}/api"
            f"?api={INSHORT_API_KEY}"
            f"&url={encoded_url}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=15) as resp:
                short_data = await resp.json()

        debug["shortlink_api_response"] = short_data

        short_url = short_data.get("shortenedUrl")

        if not short_url:
            debug["error"] = "Shortlink creation failed"
            return web.json_response(debug, status=500)

        debug["short_url"] = short_url

        # ─────────────────────────
        # 7️⃣ WHITE THEME REDIRECT
        # ─────────────────────────
        html = f"""
<!DOCTYPE html>
<html>
<head>
<title>Verification</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="2;url={short_url}">
<style>
body {{
  background:#ffffff;
  color:#000;
  font-family:Arial,sans-serif;
  display:flex;
  justify-content:center;
  align-items:center;
  height:100vh;
}}
.box {{
  text-align:center;
}}
.loader {{
  width:36px;
  height:36px;
  border:4px solid #e5e7eb;
  border-top:4px solid #2563eb;
  border-radius:50%;
  margin:20px auto;
  animation:spin 1s linear infinite;
}}
@keyframes spin {{
  0% {{transform:rotate(0deg)}}
  100% {{transform:rotate(360deg)}}
}}
pre {{
  margin-top:20px;
  font-size:12px;
  background:#f4f4f4;
  padding:10px;
  border:1px solid #ddd;
  text-align:left;
}}
</style>
</head>
<body>

<div class="box">
  <h2>Verifying…</h2>
  <div class="loader"></div>
  <p>Please wait</p>
  <pre>{debug}</pre>
</div>

<script>
setTimeout(function() {{
  window.location.replace("{short_url}");
}}, 1200);
</script>

</body>
</html>
"""
        return web.Response(text=html, content_type="text/html")

    except Exception as e:
        debug["exception"] = str(e)
        return web.json_response(debug, status=500)
