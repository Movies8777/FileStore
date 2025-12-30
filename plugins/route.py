from aiohttp import web
import os

routes = web.RouteTableDef()

KOYEB_URL = os.getenv("KOYEB_URL")


# =========================
# MAIN DETECT ROUTE
# =========================
@routes.get("/detect")
async def detect_browser(request):
    user_agent = request.headers.get("User-Agent", "Unknown")

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Browser Detection</title>

<style>
body {{
    margin: 0;
    min-height: 100vh;
    background: linear-gradient(135deg, #141e30, #243b55);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial;
    color: #fff;
}}

.card {{
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
    border-radius: 18px;
    padding: 26px;
    max-width: 420px;
    width: 92%;
    box-shadow: 0 25px 45px rgba(0,0,0,0.4);
}}

h2 {{
    margin-top: 0;
    font-size: 22px;
}}

.badge {{
    display: inline-block;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 13px;
    margin-bottom: 12px;
}}

.ok {{
    background: rgba(0,255,150,0.2);
    color: #00ffa2;
}}

.warn {{
    background: rgba(255,200,0,0.2);
    color: #ffd24d;
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
    <div id="status"></div>
    <h2 id="title">Checking Browser…</h2>
    <p id="desc"></p>

    <div class="code">
        <strong>User-Agent:</strong><br>
        {user_agent}
    </div>
</div>

<script>
// =============================
// STACKOVERFLOW TELEGRAM CHECK
// =============================
function isTelegramInApp() {{
    return (
        typeof window.TelegramWebviewProxy !== "undefined" ||
        typeof window.Telegram !== "undefined" ||
        typeof window.TelegramWebApp !== "undefined" ||
        navigator.userAgent.toLowerCase().includes("telegram")
    );
}}

// OS detection
function getOS() {{
    const ua = navigator.userAgent.toLowerCase();
    if (ua.includes("android")) return "Android";
    if (ua.includes("iphone") || ua.includes("ipad")) return "iOS";
    if (ua.includes("windows")) return "Windows";
    if (ua.includes("mac")) return "macOS";
    return "Unknown";
}}

setTimeout(() => {{
    if (isTelegramInApp()) {{
        document.getElementById("status").innerHTML =
            '<span class="badge warn">Telegram In-App Browser</span>';
        document.getElementById("title").innerText =
            "Opening External Browser";
        document.getElementById("desc").innerText =
            "You are using Telegram in-app browser. Redirecting to system browser…";

        // 🔁 Redirect to KOYEB_URL
        window.location.href = "{KOYEB_URL}";
    }} else {{
        document.getElementById("status").innerHTML =
            '<span class="badge ok">External Browser</span>';
        document.getElementById("title").innerText =
            "Success!";
        document.getElementById("desc").innerText =
            "You are already using a supported browser (" + getOS() + ").";
    }}
}}, 1200);
</script>

</body>
</html>
"""

    return web.Response(text=html, content_type="text/html")


def setup_routes(app):
    app.add_routes(routes)
