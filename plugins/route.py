from aiohttp import web
from database.database import db
import aiohttp
from datetime import datetime, timedelta

routes = web.RouteTableDef()


# ---------------- ROOT ----------------
@routes.get("/", allow_head=True)
async def root_handler(request):
    return web.json_response("Movies8777 FileStore Running")


# ------------- SHORTLINK RESOLVER -------------
async def resolve_shortlink(shortlink_url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                shortlink_url,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return str(resp.url)
    except Exception:
        return shortlink_url


# ---------------- REDIRECT ----------------
@routes.get("/redirect", allow_head=True)
async def redirect_handler(request):
    redirect_id = request.query.get("id")

    if not redirect_id:
        return web.Response(
            text="<h2>Invalid Request</h2>",
            content_type="text/html",
            status=400
        )

    try:
        data = await db.get_redirect_full(redirect_id)

        if not data or not data.get("shortlink"):
            return web.Response(
                text="<h2>Link Expired</h2>",
                content_type="text/html",
                status=404
            )

        shortlink = data["shortlink"]
        user_id = data.get("user_id")
        created_at = data.get("created_at")

        # Check verification
        is_verified = False
        if user_id:
            verify = await db.get_verify_status(user_id)
            is_verified = verify.get("is_verified", False) if verify else False

        # Expiry (2 min if not verified)
        if not is_verified and created_at:
            if datetime.now() - created_at > timedelta(minutes=2):
                return web.Response(
                    text="<h2>Verification Link Expired</h2>",
                    content_type="text/html",
                    status=404
                )

        # Already verified UI
        if is_verified:
            return web.Response(
                text="""
                <html><body style="background:#000;color:#0f0;
                display:flex;align-items:center;justify-content:center;height:100vh">
                <h1>You are already verified ✅</h1>
                </body></html>
                """,
                content_type="text/html"
            )

        final_url = await resolve_shortlink(shortlink)

        html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Redirecting...</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {{
    margin:0;
    background:#000;
    color:#0ff;
    display:flex;
    align-items:center;
    justify-content:center;
    height:100vh;
    font-family:Arial;
}}
.box {{
    text-align:center;
}}
.bar {{
    width:220px;
    height:6px;
    background:#111;
    margin-top:15px;
    overflow:hidden;
}}
.fill {{
    width:0%;
    height:100%;
    background:#0ff;
    animation:load 2s linear forwards;
}}
@keyframes load {{
    to {{ width:100%; }}
}}
</style>
</head>
<body>

<div class="box">
    <h2>Preparing your link…</h2>
    <div class="bar"><div class="fill"></div></div>
</div>

<script>
fetch('/mark-visited?id={redirect_id}').catch(()=>{{}});
setTimeout(() => {{
    window.location.replace("{final_url}");
}}, 2000);
</script>

</body>
</html>
        """

        return web.Response(text=html, content_type="text/html")

    except Exception as e:
        return web.Response(
            text=f"<h2>Error</h2><p>{e}</p>",
            content_type="text/html",
            status=500
        )


# ---------------- MARK VISITED ----------------
@routes.get("/mark-visited", allow_head=True)
async def mark_visited(request):
    redirect_id = request.query.get("id")
    if redirect_id:
        try:
            await db.mark_redirect_visited(redirect_id)
        except Exception:
            pass
    return web.json_response({"status": "ok"})


# ---------------- VERIFY (AUTO REDIRECT) ----------------
@routes.get("/verify", allow_head=True)
async def verify_handler(request):
    user_id = request.query.get("user_id")
    token = request.query.get("token")

    if not user_id or not token:
        return web.Response(
            text="<h2>Invalid Request</h2>",
            content_type="text/html",
            status=400
        )

    try:
        user_id = int(user_id)
        data = await db.get_verify_status(user_id)

        if (
            not data
            or data.get("verify_token") != token
            or not data.get("link")
        ):
            return web.Response(
                text="<h2>Verification Link Invalid</h2>",
                content_type="text/html",
                status=404
            )

        shortlink = data["link"]

        html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Verify Access</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {{
    margin:0;
    height:100vh;
    background:linear-gradient(135deg,#000428,#004e92);
    display:flex;
    align-items:center;
    justify-content:center;
    font-family:Arial;
    color:white;
}}
.card {{
    background:rgba(0,0,0,.6);
    padding:40px;
    border-radius:20px;
    text-align:center;
}}
.loader {{
    width:50px;
    height:50px;
    border:4px solid rgba(255,255,255,.2);
    border-top:4px solid #0ff;
    border-radius:50%;
    margin:20px auto;
    animation:spin 1s linear infinite;
}}
@keyframes spin {{ to {{ transform:rotate(360deg); }} }}
</style>
</head>
<body>

<div class="card">
    <h1>Verify Your Access</h1>
    <p>Redirecting automatically…</p>
    <div class="loader"></div>
</div>

<script>
setTimeout(() => {{
    window.location.replace("{shortlink}");
}}, 1500);
</script>

</body>
</html>
        """

        return web.Response(text=html, content_type="text/html")

    except Exception as e:
        return web.Response(
            text=f"<h2>Error</h2><p>{e}</p>",
            content_type="text/html",
            status=500
        )
