"""Webhook delivery service for enterprise users"""
import hmac
import hashlib
import json
import httpx
from datetime import datetime, timezone
from typing import Optional


async def deliver_webhook(webhook: dict, event_type: str, payload: dict, db) -> dict:
    """Deliver a webhook event to the registered URL"""
    url = webhook.get("url")
    secret = webhook.get("secret", "")
    webhook_id = webhook.get("id")

    # Generate signature
    payload_json = json.dumps(payload, default=str)
    signature = hmac.new(
        secret.encode() if secret else b"",
        payload_json.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-LinkShield-Event": event_type,
        "X-LinkShield-Signature": signature,
        "X-LinkShield-Timestamp": datetime.now(timezone.utc).isoformat(),
        "User-Agent": "LinkShield-Webhook/1.0"
    }

    delivery_record = {
        "webhook_id": webhook_id,
        "event_type": event_type,
        "payload": payload,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, content=payload_json, headers=headers)
            delivery_record["response_status"] = resp.status_code
            delivery_record["success"] = 200 <= resp.status_code < 300
    except Exception as e:
        delivery_record["response_status"] = 0
        delivery_record["success"] = False
        delivery_record["error"] = str(e)

    await db.webhook_deliveries.insert_one(delivery_record)
    return delivery_record


async def trigger_webhooks(user_id: str, event_type: str, payload: dict, db):
    """Trigger all matching webhooks for a user"""
    webhooks = await db.webhooks.find({
        "user_id": user_id,
        "events": event_type,
        "enabled": True
    }).to_list(100)

    results = []
    for webhook in webhooks:
        result = await deliver_webhook(webhook, event_type, payload, db)
        results.append(result)
    return results
