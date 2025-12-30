from aiohttp import web
import os

routes = web.RouteTableDef()

KOYEB_URL = os.getenv("KOYEB_URL")  # e.g. https://your-app.koyeb.app


# =====================================================
# /telegram → DETECT TELEGRAM IN-APP & REDIRECT
# =====================================================
@routes.get("/telegram/{user_id}/{page_token}")
async def detect_telegram(request):
    user_id = request.match_info["user_id"]
    page_token = request.match_info["page_token"]

    verifying_url = f"{KOYEB_URL}/verifying/{user_id}/{page_token}"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Checking Browser</title>

<style>
body {{
    margin: 0;
    height: 100vh;
    background: linear-gradient(135deg, #141e30, #243b55);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial;
    color: #fff;
}}

.box {{
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
    border-radius: 18px;
    padding: 28px;
    max-width: 360px;
    width: 92%;
    text-align: center;
    box-shadow: 0 25px 40px rgba(0,0,0,0.4);
}}

.loader {{
    width: 50px;
    height: 50px;
    border: 4px solid rgba(255,255,255,0.2);
    border-top: 4px solid #00d4ff;
    border-radius: 50%;
    margin: 0 auto 18px;
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
    <h2>Checking browser…</h2>
    <p>Please wait</p>
</div>

<script>
// StackOverflow Telegram in-app detection
function isTelegramInApp() {{
    return (
        typeof window.TelegramWebviewProxy !== "undefined" ||
        typeof window.Telegram !== "undefined" ||
        typeof window.TelegramWebApp !== "undefined" ||
        navigator.userAgent.toLowerCase().includes("telegram")
    );
}}

setTimeout(() => {{
    // In BOTH cases we move to /verifying/
    // Telegram → forces external browser
    // Normal browser → simple redirect
    window.location.href = "{verifying_url}";
}}, 1000);
</script>

</body>
</html>
"""

    return web.Response(text=html, content_type="text/html")


# =====================================================
# /verifying → EXTERNAL BROWSER DEBUG SUCCESS
# =====================================================
@routes.get("/verifying/{user_id}/{page_token}")
async def verifying_debug(request):
    user_id = request.match_info["user_id"]
    page_token = request.match_info["page_token"]
    ua = request.headers.get("User-Agent", "Unknown")

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Verification Debug</title>

<style>
body {{
    margin: 0;
    min-height: 100vh;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial;
    color: #fff;
}}

.card {{
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(12px);
    border-radius: 18px;
    padding: 26px;
    max-width: 420px;
    width: 94%;
    box-shadow: 0 30px 45px rgba(0,0,0,0.45);
}}

.badge {{
    display: inline-block;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    background: rgba(0,255,150,0.25);
    color: #00ff9c;
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
    <span class="badge">External Browser Detected</span>
    <h2>Debug Successful ✅</h2>
    <p>This page is opened outside Telegram in-app browser.</p>

    <div class="code">
        <strong>User ID:</strong> {user_id}<br><br>
        <strong>Page Token:</strong> {page_token}<br><br>
        <strong>User-Agent:</strong><br>{ua}
    </div>
</div>
</body>
</html>
"""

    return web.Response(text=html, content_type="text/html")


def setup_routes(app):
    app.add_routes(routes)
