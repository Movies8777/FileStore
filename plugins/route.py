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


@routes.get("/telegram/{user_id}/{page_token}", allow_head=True)
async def telegram_verify(request):
    try:
        # 1️⃣ URL PARAMS
        user_id = int(request.match_info["user_id"])
        page_token = request.match_info["page_token"]

        if not BOT_USERNAME:
            return error_page("Service misconfigured")

        # 2️⃣ DB CHECK
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

        # 4️⃣ SHORTLINK
        if not INSHORT_API_KEY:
            return error_page("Service unavailable")

        encoded_url = urllib.parse.quote(telegram_link, safe="")
        api_url = (
            f"https://{SHORT_URL}/api"
            f"?api={INSHORT_API_KEY}"
            f"&url={encoded_url}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=15) as resp:
                short_data = await resp.json()

        short_url = short_data.get("shortenedUrl")
        if not short_url:
            return error_page("Redirection failed")

        # 5️⃣ FINAL PAGE
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Verification</title>
  <meta http-equiv="refresh" content="2;url={short_url}">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      background:#ffffff;
      font-family: 'Segoe UI', Arial, sans-serif;
      display:flex;
      justify-content:center;
      align-items:center;
      height:100vh;
      margin:0;
      color:#0f172a;
    }}
    .card {{
      background:#ffffff;
      padding:32px 28px;
      border-radius:16px;
      box-shadow:0 20px 40px rgba(15,23,42,0.08);
      text-align:center;
      max-width:420px;
      width:100%;
      animation:fadeIn 0.6s ease-out;
    }}
    h2 {{
      margin:0 0 10px;
      font-size:22px;
      font-weight:600;
    }}
    p {{
      margin:0;
      color:#64748b;
      font-size:15px;
    }}
    .loader {{
      margin:24px auto;
      width:52px;
      height:52px;
      border-radius:50%;
      border:5px solid #e5e7eb;
      border-top-color:#2563eb;
      animation:spin 1s linear infinite;
    }}
    .pulse {{
      width:12px;
      height:12px;
      background:#2563eb;
      border-radius:50%;
      margin:16px auto 0;
      animation:pulse 1.4s infinite ease-in-out;
    }}
    @keyframes spin {{
      to {{ transform:rotate(360deg); }}
    }}
    @keyframes pulse {{
      0% {{ transform:scale(1); opacity:1; }}
      50% {{ transform:scale(1.6); opacity:0.4; }}
      100% {{ transform:scale(1); opacity:1; }}
    }}
    @keyframes fadeIn {{
      from {{ opacity:0; transform:translateY(10px); }}
      to {{ opacity:1; transform:translateY(0); }}
    }}
  </style>
</head>
<body>
  <div class="card">
    <h2>🔐 Verifying your account</h2>
    <div class="loader"></div>
    <p>Please wait, redirecting to Telegram…</p>
    <div class="pulse"></div>
  </div>
</body>
</html>
"""
        return web.Response(text=html, content_type="text/html")

    except Exception:
        return error_page("Something went wrong")


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
      border-radius:14px;
      box-shadow:0 10px 30px rgba(0,0,0,0.08);
    }}
    h3 {{ margin-bottom:8px; }}
    p {{ color:#64748b; }}
  </style>
</head>
<body>
  <div class="box">
    <h3>⚠️ {message}</h3>
    <p>Please try again later</p>
  </div>
</body>
</html>
"""
    return web.Response(text=html, content_type="text/html", status=400)


def setup_routes(app):
    app.add_routes(routes)
