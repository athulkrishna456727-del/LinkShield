"""Priority queue service using Redis"""
import os
import json
import redis.asyncio as redis
from datetime import datetime, timezone

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

_redis_pool = None


async def get_redis():
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_pool


PLAN_PRIORITY = {"enterprise": 1, "premium": 2, "free": 3}


async def enqueue_scan(user_id: str, scan_type: str, target: str, plan: str, scan_id: str):
    """Add scan to priority queue"""
    r = await get_redis()
    priority = PLAN_PRIORITY.get(plan, 3)
    job = json.dumps({
        "scan_id": scan_id,
        "user_id": user_id,
        "scan_type": scan_type,
        "target": target,
        "priority": priority,
        "plan": plan,
        "queued_at": datetime.now(timezone.utc).isoformat()
    })
    # Use sorted set with priority as score (lower = higher priority)
    # Add timestamp component to maintain FIFO within same priority
    import time
    score = priority * 1_000_000_000 + time.time()
    await r.zadd("scan_queue", {job: score})
    await r.set(f"scan_status:{scan_id}", "queued")
    return score


async def dequeue_scan():
    """Get highest priority scan from queue"""
    r = await get_redis()
    # Get lowest score (highest priority)
    results = await r.zrangebyscore("scan_queue", "-inf", "+inf", start=0, num=1)
    if results:
        job = results[0]
        await r.zrem("scan_queue", job)
        return json.loads(job)
    return None


async def get_queue_position(scan_id: str) -> dict:
    """Get position of a scan in the queue"""
    r = await get_redis()
    status = await r.get(f"scan_status:{scan_id}")
    if status == "processing" or status == "completed":
        return {"position": 0, "status": status}

    all_items = await r.zrange("scan_queue", 0, -1)
    for idx, item in enumerate(all_items):
        data = json.loads(item)
        if data.get("scan_id") == scan_id:
            return {"position": idx + 1, "status": "queued", "total_in_queue": len(all_items)}

    return {"position": 0, "status": status or "unknown"}


async def update_scan_status(scan_id: str, status: str):
    r = await get_redis()
    await r.set(f"scan_status:{scan_id}", status)
    if status == "completed":
        await r.expire(f"scan_status:{scan_id}", 3600)


async def get_queue_stats() -> dict:
    """Get queue statistics"""
    r = await get_redis()
    total = await r.zcard("scan_queue")
    all_items = await r.zrange("scan_queue", 0, -1)
    by_priority = {"enterprise": 0, "premium": 0, "free": 0}
    for item in all_items:
        data = json.loads(item)
        plan = data.get("plan", "free")
        by_priority[plan] = by_priority.get(plan, 0) + 1
    return {"total": total, "by_plan": by_priority}
