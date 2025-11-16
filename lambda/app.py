import json
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
from mangum import Mangum
import redis

load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_USERNAME = os.getenv("REDIS_USERNAME")

# Initialize Redis connection at module level for reuse across Lambda invocations
# This connection will be reused if the Lambda container is warm
_redis_client = None


def get_redis():
    """Get or create Redis client. Reuses connection across invocations."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


LOG_KEY = "webhook:requests"
TTL_SECONDS = 60 * 60 * 24 * 15  # 15 days

app = FastAPI(title="Mini Webhook Logger")


@app.get("/health")
def health():
    """Health check endpoint that verifies Redis connectivity."""
    try:
        r = get_redis()
        r.ping()
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        return {"status": "error", "redis": str(e)}


class LogEntry(BaseModel):
    id: str
    timestamp: str
    method: str
    path: str
    query: Dict[str, Any]
    headers: Dict[str, Any]
    client: Optional[str]
    body: str


async def log_request(request: Request) -> LogEntry:
    """Log incoming request to Redis."""
    body_bytes = await request.body()

    entry = LogEntry(
        id=str(int(time.time() * 1000)),
        timestamp=datetime.now(timezone.utc).isoformat(),
        method=request.method,
        path=request.url.path,
        query=dict(request.query_params),
        headers={k: v for k, v in request.headers.items()},
        client=request.client.host if request.client else None,
        body=body_bytes.decode("utf-8", errors="replace"),
    )

    # Save in Redis
    r = get_redis()
    r.lpush(LOG_KEY, entry.json())

    # Reset TTL on each insert
    r.expire(LOG_KEY, TTL_SECONDS)

    return entry


@app.get("/_logs", response_model=List[LogEntry])
def list_logs(limit: int = 50, offset: int = 0):
    """List logged webhook requests."""
    r = get_redis()
    raw_entries = r.lrange(LOG_KEY, offset, offset + limit - 1)
    return [LogEntry(**json.loads(entry)) for entry in raw_entries]


@app.delete("/_logs/clear")
def clear_logs():
    """Clear all logged webhook requests."""
    r = get_redis()
    r.delete(LOG_KEY)
    return {"status": "ok", "message": "logs cleared"}


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(full_path: str, request: Request):
    """Catch-all endpoint that logs any webhook request."""
    entry = await log_request(request)
    return {
        "full_path": full_path,
        "status": "logged",
        "id": entry.id,
        "method": entry.method,
        "timestamp": entry.timestamp,
        "path": entry.path,
    }


# Lambda handler - Mangum adapter wraps the FastAPI app
handler = Mangum(app, lifespan="off")

