from aiohttp import web
import os
import json

from database.database import db

routes = web.RouteTableDef()


@routes.get("/telegram/{user_id}/{page_token}", allow_head=True)
async def telegram_verify_debug(request):
    try:
        user_id = int(request.match_info["user_id"])
        page_token = request.match_info["page_token"]

        # Fetch verify data from DB
        user = await db.get_verify_status(user_id)

        if not user:
            return web.json_response(
                {
                    "status": "ERROR",
                    "reason": "User not found in database",
                    "user_id": user_id,
                    "page_token_from_url": page_token
                },
                status=404
            )

        return web.json_response(
            {
                "status": "OK",
                "user_id": user_id,
                "page_token_from_url": page_token,
                "page_token_in_db": user.get("page_token"),
                "verify_token": user.get("verify_token"),
                "is_verified": user.get("is_verified"),
                "verified_time": user.get("verified_time")
            },
            status=200
        )

    except Exception as e:
        return web.json_response(
            {
                "status": "ERROR",
                "exception": str(e)
            },
            status=500
        )


# APP SETUP
def setup_routes(app):
    app.add_routes(routes)
