from aiohttp import web
import os
import urllib.parse
import aiohttp

from database.database import db

routes = web.RouteTableDef()

# ENV VARIABLES (MUST BE SET IN KOYEB)
BOT_USERNAME = os.getenv("BOT_USERNAME")       # without @
SHORT_URL = os.getenv("SHORTLINK_URL")
INSHORT_API_KEY = os.getenv("SHORTLINK_API")  # inshorturl api key


@routes.get("/telegram/{user_id}/{page_token}", allow_head=True)
async def telegram_verify(request):
    debug = {}

    try:
        # ────────────────
        # 1️⃣ URL PARAMS
        # ────────────────
        user_id = int(request.match_info["user_id"])
        page_token = request.match_info["page_token"]

        debug["user_id"] = user_id
        debug["page_token_from_url"] = page_token
        debug["bot_username"] = BOT_USERNAME

        if not BOT_USERNAME:
            debug["error"] = "BOT_USERNAME env not set"
            return web.json_response(debug, status=500)

        # ────────────────
        # 2️⃣ DB CHECK
        # ────────────────
        user = await db.get_verify_status(user_id)

        if not user:
            debug["error"] = "User not found in DB"
            return web.json_response(debug, status=404)

        debug["page_token_in_db"] = user.get("page_token")
        debug["verify_token"] = user.get("verify_token")
        debug["is_verified"] = user.get("is_verified")
        debug["verified_time"] = user.get("verified_time")

        if user.get("page_token") != page_token:
            debug["error"] = "Page token mismatch"
            return web.json_response(debug, status=404)

        if not user.get("verify_token"):
            debug["error"] = "Verify token missing"
            return web.json_response(debug, status=400)

        # ────────────────
        # 3️⃣ TELEGRAM LINK
        # ────────────────
        telegram_link = (
            f"https://t.me/{BOT_USERNAME}"
            f"?start=verify_{user['verify_token']}"
        )

        debug["telegram_link"] = telegram_link

        # ────────────────
        # 4️⃣ SHORTLINK (SHORTURL)
        # ────────────────
        if not INSHORT_API_KEY:
            debug["error"] = "INSHORT_API_KEY env not set"
            return web.json_response(debug, status=500)

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

        # ────────────────
        # 5️⃣ FINAL PAGE
        # ────────────────
        html = f"""
<!DOCTYPE html>
<html>
<head>
  <title>Verification</title>
  <meta http-equiv="refresh" content="2;url={short_url}">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      background:#020617;
      color:white;
      font-family:Arial;
      display:flex;
      justify-content:center;
      align-items:center;
      height:100vh;
    }}
    .box {{
      text-align:center;
      max-width:520px;
      padding:20px;
    }}
    .loader {{
      margin:20px auto;
      width:48px;
      height:48px;
      border:6px solid #1e293b;
      border-top:6px solid #38bdf8;
      border-radius:50%;
      animation:spin 1s linear infinite;
    }}
    @keyframes spin {{
      0% {{transform:rotate(0deg)}}
      100% {{transform:rotate(360deg)}}
    }}
    pre {{
      background:#020617;
      border:1px solid #1e293b;
      padding:10px;
      color:#94a3b8;
      font-size:12px;
      text-align:left;
      overflow:auto;
    }}
  </style>
</head>
<body>
  <div class="box">
    <h2>🔐 Verification in Progress</h2>
    <div class="loader"></div>
    <p>You will be redirected automatically</p>
    <pre>{debug}</pre>
  </div>
</body>
</html>
"""
        return web.Response(text=html, content_type="text/html")

    except Exception as e:
        debug["exception"] = str(e)
        return web.json_response(debug, status=500)


def setup_routes(app):
    app.add_routes(routes)
