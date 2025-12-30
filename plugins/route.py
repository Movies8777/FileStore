from aiohttp import web
import os

routes = web.RouteTableDef()

KOYEB_URL = os.getenv("KOYEB_URL")  # example: https://yourapp.koyeb.app


# ======================================================
# /telegram → DETECT TELEGRAM IN-APP & FORCE EXTERNAL
# ======================================================
@routes.get("/telegram/{user_id}/{page_token}")
async def telegram_detect(request):
    user_id = request.match_info["user_id"]
    page_token = request.match_info["page_token"]

    redirect_url = f"{KOYEB_URL}/verifying/{user_id}/{page_token}"

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Opening Browser</title>

<style>
body {{
    margin: 0;
    height: 100vh;
    background: #0f2027;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: Arial, sans-serif;
    color: #fff;
}}

.box {{
    text-align: center;
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
    padding: 28px;
    border-radius: 18px;
    max-width: 360px;
    width: 92%;
    box-shadow: 0 25px 45px rgba(0,0,0,0.4);
}}

.loader {{
    width: 48px;
    height: 48px;
    border: 4px solid rgba(255,255,255,0.2);
    border-top: 4px solid #00d4ff;
    border-radius: 50%;
    margin: 0 auto 16px;
    animation: spin 1s linear infinite;
}}

@keyframes spin {{
    to {{ transform: rotate(360deg); }}
}}

h2 {{
    margin: 0 0 8px;
    font-size: 20px;
}}

p {{
    font-size: 14px;
    opacity: 0.85;
}}
</style>
</head>

<body>
<div class="box">
    <div class="loader"></div>
    <h2>Opening Secure Browser</h2>
    <p>Please wait…</p>
</div>

<script>
// =================================================
// STACKOVERFLOW TELEGRAM DETECTION (NO UA)
// =================================================
function isTelegramInApp() {{
    return (
        typeof window.TelegramWebviewProxy !== "undefined" ||
        typeof window.Telegram !== "undefined"
    );
}}

// =================================================
// FORCE OPEN SYSTEM BROWSER
// =================================================
function openExternal(url) {{
    // iOS (Safari)
    if (/iPhone|iPad|iPod/i.test(navigator.userAgent)) {{
        window.open(url, "_blank");
        return;
    }}

    // Android (Chrome)
    if (/Android/i.test(navigator.userAgent)) {{
        window.location.href = url;
        return;
    }}

    // Desktop (Windows / macOS / Linux)
    window.open(url, "_blank");
}}

setTimeout(() => {{
    if (isTelegramInApp()) {{
        openExternal("{redirect_url}");
    }} else {{
        // Already external browser
        window.location.href = "{redirect_url}";
    }}
}}, 900);
</script>

</body>
</html>
"""

    return web.Response(text=html, content_type="text/html")


# ======================================================
# /verifying → EXTERNAL BROWSER DEBUG PAGE
# ======================================================
@routes.get("/verifying/{user_id}/{page_token}")
async def verifying_page(request):
    user_id = request.match_info["user_id"]
    page_token = request.match_info["page_token"]
    ua = request.headers.get("User-Agent", "Unknown")

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>External Browser Confirmed</title>

<style>
body {{
    margin: 0;
    min-height: 100vh;
    background: linear-gradient(135deg, #141e30, #243b55);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: Arial, sans-serif;
    color: #fff;
}}

.card {{
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(12px);
    border-radius: 18px;
    padding: 26px;
    max-width: 420px;
    width: 94%;
    box-shadow: 0 30px 45px rgba(0,0,0,0.45);
}}

.badge {{
    display: inline-block;
    background: rgba(0,255,150,0.25);
    color: #00ff9c;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    margin-bottom: 12px;
}}

.code {{
    background: rgba(0,0,0,0.35);
    padding: 10px;
    border-radius: 10px;
    font-size: 12px;
    word-break: break-all;
}}
</style>
</head>

<body>
<div class="card">
    <span class="badge">External Browser</span>
    <h2>Success ✅</h2>
    <p>This page is opened outside Telegram in-app browser.</p>

    <div class="code">
        <b>User ID:</b> {user_id}<br><br>
        <b>Page Token:</b> {page_token}<br><br>
        <b>User-Agent:</b><br>{ua}
    </div>
</div>
</body>
</html>
"""

    return web.Response(text=html, content_type="text/html")


def setup_routes(app):
    app.add_routes(routes)
