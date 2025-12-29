from aiohttp import web
import os
from database.database import db

routes = web.RouteTableDef()

BOT_USERNAME = os.getenv("BOT_USERNAME")


# =========================
# 🔍 FULL BROWSER DEBUG
# =========================
def detect_browser(request):
    ua = request.headers.get("User-Agent", "").lower()

    browser = "Unknown"
    platform = "Unknown"
    in_app = False

    # Platform detection
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
        platform = "Desktop/Other"

    # Browser detection
    if "telegram" in ua or "tgweb" in ua:
        browser = "Telegram In-App"
        in_app = True
    elif "chrome" in ua and "edg" not in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "edg" in ua:
        browser = "Edge"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "opera" in ua or "opr" in ua:
        browser = "Opera"

    return browser, platform, in_app, ua


# =========================
# 🧪 DEBUG ROUTE ONLY
# =========================
@routes.get("/telegram/{user_id}/{page_token}", allow_head=True)
async def telegram_verify(request):
    try:
        user_id = int(request.match_info["user_id"])
        page_token = request.match_info["page_token"]

        if not BOT_USERNAME:
            return error_page("Service unavailable")

        # DB check (kept for safety)
        user = await db.get_verify_status(user_id)
        if not user or user.get("page_token") != page_token:
            return error_page("Invalid or expired link")

        browser, platform, in_app, ua = detect_browser(request)

        # Console log
        print(
            f"[DEBUG] user={user_id} | platform={platform} | browser={browser} | in_app={in_app}"
        )

        # DEBUG PAGE
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Browser Debug</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      margin: 0;
      height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: Arial, sans-serif;
      background: #f8fafc;
    }}
    .card {{
      width: 92%;
      max-width: 460px;
      background: #ffffff;
      padding: 24px;
      border-radius: 16px;
      box-shadow: 0 12px 30px rgba(0,0,0,0.12);
    }}
    h2 {{
      margin-bottom: 14px;
      color: #0f172a;
    }}
    p {{
      margin: 6px 0;
      font-size: 14px;
      color: #334155;
    }}
    .ua {{
      margin-top: 12px;
      font-size: 12px;
      color: #64748b;
      word-break: break-all;
    }}
    .tag {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 8px;
      background: #e5edff;
      color: #1e40af;
      font-size: 12px;
      margin-top: 6px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h2>Browser Debug Info</h2>

    <p><b>User ID:</b> {user_id}</p>
    <p><b>Platform:</b> {platform}</p>
    <p><b>Browser:</b> {browser}</p>
    <p><b>Telegram In-App:</b> {in_app}</p>

    <div class="tag">Debug Mode</div>

    <div class="ua">
      <b>User-Agent:</b><br>
      {ua}
    </div>
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
    return web.Response(
        text=f"<h3 style='font-family:Arial;text-align:center;margin-top:40px'>{message}</h3>",
        content_type="text/html",
        status=400
    )


def setup_routes(app):
    app.add_routes(routes)
