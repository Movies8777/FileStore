from aiohttp import web
import os
import urllib.parse
import aiohttp
import re
import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import Optional, Dict, Any

from database.database import db

routes = web.RouteTableDef()

# ========== ENV VARIABLES (MUST BE SET IN KOYEB) ==========
BOT_USERNAME = os.getenv("BOT_USERNAME")       # without @
SHORT_URL = os.getenv("SHORTLINK_URL")
INSHORT_API_KEY = os.getenv("SHORTLINK_API")  # inshorturl api key
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "5"))
ALLOWED_DOMAINS = ["t.me", "telegram.me"]

# ========== SETUP LOGGING ==========
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== VALIDATION FUNCTIONS ==========
def validate_user_id(user_id_str: str) -> tuple[bool, Optional[int]]:
    """Validate and convert user_id"""
    if not user_id_str.isdigit():
        return False, None
    try:
        user_id = int(user_id_str)
        # Telegram user IDs are positive integers
        if user_id <= 0:
            return False, None
        # Reasonable upper limit
        if user_id > 10**9:
            return False, None
        return True, user_id
    except (ValueError, TypeError):
        return False, None

def validate_page_token(token: str) -> bool:
    """Validate page token format"""
    # Should be alphanumeric with hyphens/underscores, reasonable length
    pattern = r'^[a-zA-Z0-9_-]{16,64}$'
    return bool(re.match(pattern, token))

def validate_url(url: str, allowed_domains: list = None) -> bool:
    """Validate URL format and domain"""
    if allowed_domains is None:
        allowed_domains = ALLOWED_DOMAINS
    
    try:
        parsed = urlparse(url)
        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Must be http or https
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Check if domain is allowed
        domain = parsed.netloc.lower()
        if allowed_domains and domain not in allowed_domains:
            return False
            
        return True
    except Exception:
        return False

# ========== SHORTLINK SERVICE ==========
class ShortlinkService:
    """Service for creating and validating shortlinks"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.cache = {}  # Simple in-memory cache
        self.cache_timeout = timedelta(minutes=5)
        
    async def create_shortlink(self, original_url: str, session: aiohttp.ClientSession) -> Optional[str]:
        """Create a shortlink with retry logic"""
        # Validate URL first
        if not validate_url(original_url):
            logger.error(f"Invalid URL for shortlink: {original_url}")
            return None
            
        # Check cache first
        cache_key = f"{original_url}_{self.api_key}"
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            if datetime.now() - cached_entry['timestamp'] < self.cache_timeout:
                return cached_entry['short_url']
        
        # Prepare API request
        encoded_url = urllib.parse.quote(original_url, safe="")
        api_url = (
            f"https://{self.base_url}/api"
            f"?api={self.api_key}"
            f"&url={encoded_url}"
        )
        
        # Retry logic (max 3 attempts)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with session.get(api_url, timeout=15) as resp:
                    if resp.status != 200:
                        logger.error(f"Shortlink API error: HTTP {resp.status}")
                        continue
                        
                    short_data = await resp.json()
                    
                    # Validate API response
                    if not isinstance(short_data, dict):
                        logger.error("Invalid API response format")
                        continue
                        
                    short_url = short_data.get("shortenedUrl")
                    if not short_url or not validate_url(short_url):
                        logger.error(f"Invalid short URL received: {short_url}")
                        continue
                    
                    # Cache the result
                    self.cache[cache_key] = {
                        'short_url': short_url,
                        'timestamp': datetime.now()
                    }
                    
                    logger.info(f"Shortlink created: {original_url[:50]}... -> {short_url}")
                    return short_url
                    
            except aiohttp.ClientError as e:
                logger.error(f"Shortlink API attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error in shortlink creation: {str(e)}")
                break
        
        return None

# Initialize shortlink service
shortlink_service = ShortlinkService(INSHORT_API_KEY, SHORT_URL) if INSHORT_API_KEY and SHORT_URL else None

# ========== RATE LIMITING MIDDLEWARE ==========
@web.middleware
async def rate_limit_middleware(request: web.Request, handler):
    """Basic rate limiting middleware"""
    # Get client IP (support for proxies)
    if 'X-Forwarded-For' in request.headers:
        client_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
    else:
        client_ip = request.remote
    
    # Simple in-memory rate limiting (use Redis in production)
    rate_limit_key = f"rate_limit:{client_ip}"
    rate_limit_count = getattr(request.app, 'rate_limit_data', {}).get(rate_limit_key, 0)
    
    # 60 requests per minute per IP
    if rate_limit_count >= 60:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return web.json_response(
            {"error": "Rate limit exceeded. Please try again later."},
            status=429
        )
    
    # Update rate limit count
    if not hasattr(request.app, 'rate_limit_data'):
        request.app.rate_limit_data = {}
    
    request.app.rate_limit_data[rate_limit_key] = rate_limit_count + 1
    
    # Clean old entries periodically (in production, use TTL in Redis)
    if len(request.app.rate_limit_data) > 10000:
        # Keep only recent entries (simplified)
        request.app.rate_limit_data = dict(list(request.app.rate_limit_data.items())[-5000:])
    
    return await handler(request)

# ========== MAIN ENDPOINT ==========
@routes.get("/telegram/{user_id}/{page_token}", allow_head=True)
async def telegram_verify(request):
    debug = {} if DEBUG_MODE else None
    
    try:
        # ────────────────
        # 1️⃣ VALIDATION & CONFIG CHECK
        # ────────────────
        # Validate environment variables
        if not BOT_USERNAME:
            error_msg = "BOT_USERNAME environment variable not configured"
            logger.critical(error_msg)
            return web.Response(
                text="Service temporarily unavailable. Please try again later.",
                status=500
            )
        
        if not INSHORT_API_KEY or not SHORT_URL:
            error_msg = "Shortlink service not configured"
            logger.critical(error_msg)
            return web.Response(
                text="Service temporarily unavailable. Please try again later.",
                status=500
            )
        
        # Validate input parameters
        user_id_str = request.match_info["user_id"]
        page_token = request.match_info["page_token"]
        
        is_valid_user_id, user_id = validate_user_id(user_id_str)
        if not is_valid_user_id:
            logger.warning(f"Invalid user_id format: {user_id_str}")
            return web.Response(
                text="Invalid request parameters.",
                status=400
            )
        
        if not validate_page_token(page_token):
            logger.warning(f"Invalid page_token format: {page_token}")
            return web.Response(
                text="Invalid request parameters.",
                status=400
            )
        
        # Log request
        logger.info(f"Verification request - user_id: {user_id}, page_token: {page_token[:8]}...")
        
        if debug is not None:
            debug["user_id"] = user_id
            debug["page_token_from_url"] = page_token[:8] + "..."  # Only log first 8 chars
            debug["bot_username"] = BOT_USERNAME

        # ────────────────
        # 2️⃣ DATABASE CHECK WITH TIMEOUT
        # ────────────────
        try:
            user = await db.get_verify_status(user_id)
        except Exception as db_error:
            logger.error(f"Database error for user {user_id}: {str(db_error)}")
            return web.Response(
                text="Service temporarily unavailable. Please try again later.",
                status=503
            )
        
        if not user:
            logger.warning(f"User not found in database: {user_id}")
            return web.Response(
                text="Verification link expired or invalid.",
                status=404
            )
        
        # Check session timeout
        if user.get("created_time"):
            try:
                created_time = datetime.fromisoformat(user["created_time"].replace('Z', '+00:00'))
                timeout_minutes = SESSION_TIMEOUT_MINUTES
                if datetime.utcnow() - created_time > timedelta(minutes=timeout_minutes):
                    logger.info(f"Verification session expired for user {user_id}")
                    return web.Response(
                        text="Verification link has expired. Please request a new one.",
                        status=410  # Gone
                    )
            except (ValueError, TypeError):
                pass  # Continue if timestamp is invalid
        
        # Validate page token
        db_page_token = user.get("page_token")
        if db_page_token != page_token:
            logger.warning(f"Page token mismatch for user {user_id}")
            return web.Response(
                text="Verification link expired or invalid.",
                status=404
            )
        
        # Check if already verified
        if user.get("is_verified"):
            logger.info(f"User already verified: {user_id}")
            return web.Response(
                text="You are already verified. No further action needed.",
                status=200
            )
        
        # Check verify token
        verify_token = user.get("verify_token")
        if not verify_token:
            logger.error(f"Verify token missing for user {user_id}")
            return web.Response(
                text="Invalid verification data. Please request a new verification link.",
                status=400
            )
        
        if debug is not None:
            debug["is_verified"] = user.get("is_verified")
            debug["session_age"] = user.get("created_time")

        # ────────────────
        # 3️⃣ TELEGRAM LINK GENERATION
        # ────────────────
        telegram_link = (
            f"https://t.me/{BOT_USERNAME}"
            f"?start=verify_{verify_token}"
        )
        
        # Validate the Telegram link
        if not validate_url(telegram_link):
            logger.error(f"Generated invalid Telegram link for user {user_id}")
            return web.Response(
                text="Service configuration error. Please contact administrator.",
                status=500
            )
        
        if debug is not None:
            debug["telegram_link"] = telegram_link

        # ────────────────
        # 4️⃣ SHORTLINK CREATION
        # ────────────────
        if shortlink_service is None:
            logger.critical("Shortlink service not initialized")
            return web.Response(
                text="Service temporarily unavailable. Please try again later.",
                status=500
            )
        
        async with aiohttp.ClientSession() as session:
            try:
                short_url = await shortlink_service.create_shortlink(telegram_link, session)
                
                if not short_url:
                    logger.error(f"Failed to create shortlink for user {user_id}")
                    # Fallback to original Telegram link
                    short_url = telegram_link
                    logger.info(f"Using original Telegram link as fallback for user {user_id}")
                
                if debug is not None:
                    debug["short_url"] = short_url

            except Exception as shortlink_error:
                logger.error(f"Shortlink creation failed for user {user_id}: {str(shortlink_error)}")
                # Fallback to original link
                short_url = telegram_link
                if debug is not None:
                    debug["shortlink_error"] = str(shortlink_error)

        # ────────────────
        # 5️⃣ FINAL RESPONSE
        # ────────────────
        # Security headers
        headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer"
        }
        
        # HTML with secure redirect
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Verification</title>
    <meta name="description" content="Redirecting to Telegram for verification">
    <meta http-equiv="refresh" content="2;url={short_url}">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            max-width: 500px;
            width: 90%;
        }}
        .loader {{
            margin: 2rem auto;
            width: 50px;
            height: 50px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        h1 {{
            margin-bottom: 1rem;
            font-weight: 600;
        }}
        p {{
            margin-bottom: 0.5rem;
            opacity: 0.9;
        }}
        .warning {{
            margin-top: 2rem;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            font-size: 0.9rem;
        }}
        a {{
            color: #a78bfa;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Verification Required</h1>
        <p>Redirecting to Telegram...</p>
        <div class="loader"></div>
        <p>Please complete verification in Telegram to continue.</p>
        <div class="warning">
            <p>If you are not redirected automatically, <a href="{short_url}" id="manual-link">click here</a>.</p>
        </div>
    </div>
    <script>
        // Auto-redirect with safety check
        setTimeout(function() {{
            window.location.href = "{short_url}";
        }}, 2000);
        
        // Manual link click tracking
        document.getElementById('manual-link').addEventListener('click', function(e) {{
            console.log('Manual redirect triggered');
        }});
        
        // Log redirect attempt
        console.log('Starting verification redirect to Telegram');
    </script>
</body>
</html>
"""
        
        return web.Response(text=html, content_type="text/html", headers=headers)

    except Exception as e:
        # Log the full error with traceback
        logger.exception(f"Unexpected error in telegram_verify endpoint")
        
        # Return generic error to user
        error_response = web.Response(
            text="An unexpected error occurred. Please try again later.",
            status=500
        )
        
        # Only include debug info in debug mode
        if DEBUG_MODE:
            debug["exception"] = str(e)
            error_response = web.json_response(
                {"error": "Internal server error", "debug": debug},
                status=500
            )
        
        return error_response

# ========== ADDITIONAL ENDPOINTS ==========
@routes.get("/health", allow_head=True)
async def health_check(request):
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        await db.health_check()
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "telegram-verification",
            "version": "1.0.0"
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return web.json_response(
            {"status": "unhealthy", "error": str(e)},
            status=503
        )

@routes.get("/", allow_head=True)
async def root_handler(request):
    """Root endpoint"""
    return web.Response(
        text="Telegram Verification Service is running. Use /telegram/{user_id}/{token} for verification.",
        content_type="text/plain"
    )

# ========== SETUP FUNCTION ==========
def setup_routes(app):
    """Setup routes with middleware"""
    # Add rate limiting middleware
    app.middlewares.append(rate_limit_middleware)
    
    # Add routes
    app.add_routes(routes)
    
    # Add error handlers
    @web.middleware
    async def error_middleware(request, handler):
        try:
            return await handler(request)
        except web.HTTPException as ex:
            # Pass through HTTP exceptions
            raise
        except Exception as e:
            logger.exception(f"Unhandled exception in middleware")
            return web.Response(
                text="Internal server error",
                status=500
            )
    
    app.middlewares.append(error_middleware)
    
    # Validate configuration on startup
    config_errors = []
    if not BOT_USERNAME:
        config_errors.append("BOT_USERNAME")
    if not SHORT_URL:
        config_errors.append("SHORTLINK_URL")
    if not INSHORT_API_KEY:
        config_errors.append("SHORTLINK_API")
    
    if config_errors:
        logger.critical(f"Missing configuration: {', '.join(config_errors)}")
        # Don't crash, but log critical error
    
    logger.info("Routes and middleware setup complete")
