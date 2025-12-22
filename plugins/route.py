from aiohttp import web
import os
import aiohttp

routes = web.RouteTableDef()

BOT_USERNAME = os.getenv("BOT_USERNAME")
SHORTLINK_API = os.getenv("SHORTLINK_API")
SHORTLINK_URL = os.getenv("SHORTLINK_URL")

# TEMP STORE (replace with DB or bot API)
PAGE_TOKEN_MAP = {
    # "page_token": "verify_token"
}

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("Movies8777 FileStore")

@routes.get("/link/{page_token}", allow_head=True)
async def verify_page(request):
    page_token = request.match_info["page_token"]

    if page_token not in PAGE_TOKEN_MAP:
        return web.Response(text="Invalid or expired link", status=404)

    verify_token = PAGE_TOKEN_MAP[page_token]

    telegram_url = f"https://t.me/{BOT_USERNAME}?start=verify_{verify_token}"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            SHORTLINK_URL,
            params={"api": SHORTLINK_API, "url": telegram_url}
        ) as resp:
            data = await resp.json()

    short_url = data.get("shortenedUrl")
    if not short_url:
        return web.Response(text="Shortlink error", status=500)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Redirecting...</title>
      <meta http-equiv="refresh" content="2;url={short_url}">
      <style>
        body {{
          background:#0f2027;
          color:white;
          height:100vh;
          display:flex;
          justify-content:center;
          align-items:center;
          font-family:Arial;
        }}
        .box {{ text-align:center; }}
        .loader {{
          width:40px;
          height:40px;
          border:4px solid #fff;
          border-top:4px solid transparent;
          border-radius:50%;
          animation:spin 1s linear infinite;
          margin:20px auto;
        }}
        @keyframes spin {{
          to {{ transform:rotate(360deg); }}
        }}
      </style>
    </head>
    <body>
      <div class="box">
        <h2>🔐 Verification in progress</h2>
        <div class="loader"></div>
        <p>Please wait…</p>
      </div>
    </body>
    </html>
    """

    return web.Response(text=html, content_type="text/html")
