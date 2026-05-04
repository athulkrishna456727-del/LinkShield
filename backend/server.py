from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
import secrets
import hashlib
import re
import bcrypt
import jwt
import hmac
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import base64

from services.scanners import scan_url_full, scan_file_full, extract_url_iocs, extract_file_iocs
from services.queue import enqueue_scan, dequeue_scan, update_scan_status, get_queue_position, get_queue_stats
from services.reports import generate_scan_pdf, generate_summary_pdf, send_report_email
from services.webhooks import trigger_webhooks
from routes.enterprise import _build_routes as _build_enterprise_routes

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# App setup
app = FastAPI(title="Link Shield API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# DB
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME')
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Auth
JWT_SECRET = os.environ.get('JWT_SECRET', 'link-shield-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Encryption for secrets
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(JWT_SECRET.encode()).digest())
fernet = Fernet(_fernet_key)

# Plan configuration
PLAN_CONFIG = {
    "free": {"credits_per_month": 50, "priority": 3, "api_calls_per_day": 0, "max_team_members": 0, "webhooks": False, "reports": False, "ioc_export": False},
    "premium": {"credits_per_month": 500, "priority": 2, "api_calls_per_day": 1000, "max_team_members": 0, "webhooks": False, "reports": True, "ioc_export": True},
    "enterprise": {"credits_per_month": 999999, "priority": 1, "api_calls_per_day": 10000, "max_team_members": 50, "webhooks": True, "reports": True, "ioc_export": True}
}

SCAN_COSTS = {"url": {"free": 5, "premium": 3, "enterprise": 1}, "file": {"free": 10, "premium": 6, "enterprise": 2}}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------- HELPERS ----------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, email: str, role: str) -> str:
    return jwt.encode({"user_id": user_id, "email": email, "role": role, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, JWT_SECRET, algorithm=JWT_ALGORITHM)

def encrypt_value(val: str) -> str:
    return fernet.encrypt(val.encode()).decode()

def decrypt_value(val: str) -> str:
    return fernet.decrypt(val.encode()).decode()

def mask_key(val: str) -> str:
    if len(val) <= 8: return "****"
    return val[:4] + "*" * (len(val) - 8) + val[-4:]

def generate_api_key() -> str:
    return f"ls_{secrets.token_hex(32)}"


# ---------- MODELS ----------

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: str
    username: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    username: str
    name: str
    role: str = "user"
    plan: str = "free"
    credits: int = 50
    api_key: Optional[str] = None
    created_at: str

class ScanURLRequest(BaseModel):
    url: str
    sensitivity: str = "normal"  # low, normal, high, aggressive

class UpdatePlanRequest(BaseModel):
    plan: str

class UpdateRoleRequest(BaseModel):
    role: str

class CreditAdjust(BaseModel):
    amount: int
    reason: str = ""

class CreateAdminRequest(BaseModel):
    email: EmailStr
    name: str
    temporary_password: str

class WebhookCreate(BaseModel):
    url: str
    events: List[str]
    secret: Optional[str] = None

class TeamCreate(BaseModel):
    name: str

class TeamMemberAdd(BaseModel):
    email: str
    role: str = "member"

class ReportScheduleCreate(BaseModel):
    frequency: str  # daily, weekly, monthly
    format: str = "pdf"

class PaymentSettingsUpdate(BaseModel):
    gateway: str = "razorpay"
    key_id: str
    key_secret: str
    is_active: bool = True

class PriceUpdate(BaseModel):
    premium_price: int
    enterprise_price: int


# ---------- AUTH MIDDLEWARE ----------

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def get_owner_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return user

def require_plan(min_plan: str):
    """Dependency factory for plan-gating"""
    plan_order = {"free": 0, "premium": 1, "enterprise": 2}
    async def checker(user: User = Depends(get_current_user)):
        if plan_order.get(user.plan, 0) < plan_order.get(min_plan, 0):
            raise HTTPException(status_code=403, detail=f"This feature requires {min_plan} plan or above")
        return user
    return checker

async def get_user_by_api_key(request: Request) -> User:
    """Auth via API key header"""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    user = await db.users.find_one({"api_key": api_key}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # Check rate limit
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if user.get("api_call_reset") != today:
        await db.users.update_one({"id": user["id"]}, {"$set": {"api_call_count": 0, "api_call_reset": today}})
        user["api_call_count"] = 0
    plan_config = PLAN_CONFIG.get(user.get("plan", "free"), PLAN_CONFIG["free"])
    max_calls = plan_config["api_calls_per_day"]
    if max_calls == 0:
        raise HTTPException(status_code=403, detail="API access requires Premium or Enterprise plan")
    if user.get("api_call_count", 0) >= max_calls:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded ({max_calls} calls/day)")
    await db.users.update_one({"id": user["id"]}, {"$inc": {"api_call_count": 1}})
    return User(**user)


# ---------- AUDIT ----------

async def create_audit_log(action_type: str, performed_by: str, target_user: str = None, details: str = ""):
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action_type": action_type,
        "performed_by": performed_by,
        "target_user": target_user,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

async def create_notification(user_id: str, notif_type: str, message: str):
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": notif_type,
        "message": message,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })


# ==================== AUTH ROUTES ====================

@api_router.post("/auth/signup")
async def signup(data: UserSignup):
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not re.match(r'^[a-z0-9_]{3,20}$', data.username):
        raise HTTPException(status_code=400, detail="Username: 3-20 chars, lowercase letters, numbers, underscore only")
    existing = await db.users.find_one({"$or": [{"email": data.email}, {"username": data.username}]})
    if existing:
        if existing.get("email") == data.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail="Username already taken")

    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id, "email": data.email, "username": data.username,
        "name": data.name, "password_hash": hash_password(data.password),
        "role": "user", "plan": "free", "credits": 50,
        "api_key": None, "api_call_count": 0, "api_call_reset": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    token = create_token(user_id, data.email, "user")
    user_doc.pop("password_hash")
    user_doc.pop("_id", None)
    return {"token": token, "user": user_doc}


@api_router.post("/auth/login")
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user['id'], user['email'], user['role'])
    user_response = {k: v for k, v in user.items() if k not in ("password_hash", "_id")}
    return {"token": token, "user": user_response}


@api_router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0, "password_hash": 0})
    return user_doc


# ==================== SCANNING ROUTES ====================

@api_router.post("/scan/url")
async def scan_url(data: ScanURLRequest, user: User = Depends(get_current_user)):
    cost = SCAN_COSTS["url"].get(user.plan, 5)
    user_doc = await db.users.find_one({"id": user.id})
    if user_doc["credits"] < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    sensitivity = data.sensitivity if data.sensitivity in ("low", "normal", "high", "aggressive") else "normal"
    scan_id = str(uuid.uuid4())
    await db.users.update_one({"id": user.id}, {"$inc": {"credits": -cost}})
    await enqueue_scan(user.id, "url", data.url, user.plan, scan_id)
    await update_scan_status(scan_id, "processing")

    # Run full scan with all engines
    scan_result = await scan_url_full(data.url, sensitivity, db, user.plan)

    scan_doc = {
        "id": scan_id, "user_id": user.id, "scan_type": "url",
        "target": data.url, "status": "completed",
        "sensitivity": sensitivity,
        "risk_score": scan_result["risk_score"],
        "risk_level": scan_result["risk_level"],
        "explanations": scan_result["explanations"],
        "detections": scan_result["detections"],
        "engines_detected": scan_result["engines_detected"],
        "engines_total": scan_result["engines_total"],
        "urlhaus_detected": scan_result["urlhaus_detected"],
        "urlscan_malicious": scan_result.get("urlscan_malicious", False),
        "threats": scan_result["detections"],
        "raw_results": scan_result.get("api_results_raw", []),
        "from_cache": scan_result.get("from_cache", False),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.scans.insert_one(scan_doc)

    # Store IOCs
    iocs = scan_result.get("iocs", [])
    if iocs:
        ioc_docs = [{"scan_id": scan_id, "ioc_type": i["ioc_type"], "value": i["value"], "confidence": i["confidence"], "created_at": datetime.now(timezone.utc).isoformat()} for i in iocs]
        await db.iocs.insert_many(ioc_docs)

    await update_scan_status(scan_id, "completed")

    # Trigger webhooks for enterprise
    if user.plan == "enterprise":
        await trigger_webhooks(user.id, "scan.completed", {
            "scan_id": scan_id, "target": data.url,
            "risk_score": scan_result["risk_score"], "risk_level": scan_result["risk_level"]
        }, db)

    response = {k: v for k, v in scan_doc.items() if k not in ("_id", "raw_results")}
    response["iocs"] = iocs
    response["credits_used"] = cost
    response["credits_remaining"] = user_doc["credits"] - cost
    return response


@api_router.post("/scan/file")
async def scan_file(file: UploadFile = File(...), sensitivity: str = "normal", user: User = Depends(get_current_user)):
    cost = SCAN_COSTS["file"].get(user.plan, 10)
    user_doc = await db.users.find_one({"id": user.id})
    if user_doc["credits"] < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    if sensitivity not in ("low", "normal", "high", "aggressive"):
        sensitivity = "normal"

    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    scan_id = str(uuid.uuid4())

    await db.users.update_one({"id": user.id}, {"$inc": {"credits": -cost}})
    await enqueue_scan(user.id, "file", file.filename, user.plan, scan_id)
    await update_scan_status(scan_id, "processing")

    # Run full file scan with heuristics + APIs
    scan_result = await scan_file_full(file_bytes, file.filename, sensitivity, db, user.plan)

    scan_doc = {
        "id": scan_id, "user_id": user.id, "scan_type": "file",
        "target": file.filename, "status": "completed",
        "sensitivity": sensitivity,
        "file_hash": file_hash,
        "file_size": len(file_bytes),
        "file_type_detected": scan_result.get("file_type_detected", "unknown"),
        "risk_score": scan_result["risk_score"],
        "risk_level": scan_result["risk_level"],
        "explanations": scan_result["explanations"],
        "detections": scan_result.get("detections", []),
        "engines_detected": scan_result.get("engines_detected", 0),
        "engines_total": scan_result.get("engines_total", 0),
        "heuristic_score": scan_result.get("heuristic_result", {}).get("heuristic_score", 0),
        "heuristic_findings": scan_result.get("heuristic_result", {}).get("findings", []),
        "threats": scan_result.get("detections", []),
        "raw_results": scan_result.get("api_results_raw", []),
        "from_cache": scan_result.get("from_cache", False),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.scans.insert_one(scan_doc)

    iocs = scan_result.get("iocs", [])
    if iocs:
        ioc_docs = [{"scan_id": scan_id, "ioc_type": i["ioc_type"], "value": i["value"], "confidence": i["confidence"], "created_at": datetime.now(timezone.utc).isoformat()} for i in iocs]
        await db.iocs.insert_many(ioc_docs)

    await update_scan_status(scan_id, "completed")

    if user.plan == "enterprise":
        await trigger_webhooks(user.id, "scan.completed", {
            "scan_id": scan_id, "target": file.filename,
            "risk_score": scan_result["risk_score"], "risk_level": scan_result["risk_level"],
            "file_hash": file_hash
        }, db)

    response = {k: v for k, v in scan_doc.items() if k not in ("_id", "raw_results")}
    response["iocs"] = iocs
    response["credits_used"] = cost
    response["credits_remaining"] = user_doc["credits"] - cost
    return response


@api_router.get("/scan/{scan_id}")
async def get_scan(scan_id: str, user: User = Depends(get_current_user)):
    scan = await db.scans.find_one({"id": scan_id, "user_id": user.id}, {"_id": 0, "raw_results": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    iocs = await db.iocs.find({"scan_id": scan_id}, {"_id": 0}).to_list(100)
    scan["iocs"] = iocs
    return scan


@api_router.get("/scan/queue/status/{scan_id}")
async def get_scan_queue_status(scan_id: str, user: User = Depends(get_current_user)):
    return await get_queue_position(scan_id)


@api_router.get("/scans/history")
async def scan_history(limit: int = 50, skip: int = 0, user: User = Depends(get_current_user)):
    scans = await db.scans.find(
        {"user_id": user.id}, {"_id": 0, "raw_results": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.scans.count_documents({"user_id": user.id})
    return {"scans": scans, "total": total}


# ==================== IOC ROUTES (Premium+) ====================

@api_router.get("/iocs/scan/{scan_id}")
async def get_scan_iocs(scan_id: str, user: User = Depends(require_plan("premium"))):
    scan = await db.scans.find_one({"id": scan_id, "user_id": user.id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    iocs = await db.iocs.find({"scan_id": scan_id}, {"_id": 0}).to_list(500)
    return {"scan_id": scan_id, "iocs": iocs, "total": len(iocs)}


@api_router.get("/iocs/export/{scan_id}")
async def export_iocs(scan_id: str, format: str = "json", user: User = Depends(require_plan("premium"))):
    scan = await db.scans.find_one({"id": scan_id, "user_id": user.id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    iocs = await db.iocs.find({"scan_id": scan_id}, {"_id": 0}).to_list(500)

    if format == "csv":
        csv_lines = ["ioc_type,value,confidence"]
        for ioc in iocs:
            csv_lines.append(f"{ioc['ioc_type']},{ioc['value']},{ioc['confidence']}")
        return Response(content="\n".join(csv_lines), media_type="text/csv",
                       headers={"Content-Disposition": f"attachment; filename=iocs_{scan_id[:8]}.csv"})
    return {"scan_id": scan_id, "iocs": iocs}


@api_router.get("/iocs/all")
async def get_all_user_iocs(limit: int = 100, ioc_type: Optional[str] = None, user: User = Depends(require_plan("premium"))):
    """Get all IOCs across user's scans"""
    user_scans = await db.scans.find({"user_id": user.id}, {"id": 1, "_id": 0}).to_list(1000)
    scan_ids = [s["id"] for s in user_scans]
    query = {"scan_id": {"$in": scan_ids}}
    if ioc_type:
        query["ioc_type"] = ioc_type
    iocs = await db.iocs.find(query, {"_id": 0}).sort("confidence", -1).limit(limit).to_list(limit)
    return {"iocs": iocs, "total": len(iocs)}


# ==================== API KEY ROUTES (Premium+) ====================

@api_router.post("/apikey/generate")
async def generate_user_api_key(user: User = Depends(require_plan("premium"))):
    new_key = generate_api_key()
    await db.users.update_one({"id": user.id}, {"$set": {"api_key": new_key}})
    await create_audit_log("api_key_generated", user.id, details="API key generated")
    return {"api_key": new_key, "message": "Store this key securely - it won't be shown again in full"}


@api_router.delete("/apikey/revoke")
async def revoke_api_key(user: User = Depends(require_plan("premium"))):
    await db.users.update_one({"id": user.id}, {"$set": {"api_key": None, "api_call_count": 0}})
    await create_audit_log("api_key_revoked", user.id, details="API key revoked")
    return {"message": "API key revoked"}


@api_router.get("/apikey/usage")
async def get_api_key_usage(user: User = Depends(require_plan("premium"))):
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0})
    plan_config = PLAN_CONFIG.get(user.plan, PLAN_CONFIG["free"])
    return {
        "has_key": bool(user_doc.get("api_key")),
        "key_preview": mask_key(user_doc["api_key"]) if user_doc.get("api_key") else None,
        "calls_today": user_doc.get("api_call_count", 0),
        "daily_limit": plan_config["api_calls_per_day"],
        "reset_date": user_doc.get("api_call_reset", "")
    }


# ==================== API ENDPOINT (External API access via key) ====================

@api_router.post("/v1/scan/url")
async def api_scan_url(data: ScanURLRequest, user: User = Depends(get_user_by_api_key)):
    """External API endpoint for URL scanning"""
    cost = SCAN_COSTS["url"].get(user.plan, 5)
    user_doc = await db.users.find_one({"id": user.id})
    if user_doc["credits"] < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    sensitivity = data.sensitivity if data.sensitivity in ("low", "normal", "high", "aggressive") else "normal"
    scan_id = str(uuid.uuid4())
    await db.users.update_one({"id": user.id}, {"$inc": {"credits": -cost}})
    await update_scan_status(scan_id, "processing")

    scan_result = await scan_url_full(data.url, sensitivity, db, user.plan)

    scan_doc = {
        "id": scan_id, "user_id": user.id, "scan_type": "url",
        "target": data.url, "status": "completed", "sensitivity": sensitivity,
        "risk_score": scan_result["risk_score"], "risk_level": scan_result["risk_level"],
        "explanations": scan_result["explanations"],
        "detections": scan_result["detections"],
        "engines_detected": scan_result["engines_detected"],
        "engines_total": scan_result["engines_total"],
        "threats": scan_result["detections"],
        "raw_results": scan_result.get("api_results_raw", []),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.scans.insert_one(scan_doc)

    iocs = scan_result.get("iocs", [])
    if iocs:
        ioc_docs = [{"scan_id": scan_id, "ioc_type": i["ioc_type"], "value": i["value"], "confidence": i["confidence"], "created_at": datetime.now(timezone.utc).isoformat()} for i in iocs]
        await db.iocs.insert_many(ioc_docs)

    await update_scan_status(scan_id, "completed")
    return {
        "scan_id": scan_id, "target": data.url,
        "risk_score": scan_result["risk_score"], "risk_level": scan_result["risk_level"],
        "explanations": scan_result["explanations"],
        "detections": scan_result["detections"][:10], "iocs": iocs
    }


# ==================== REPORTS (Premium+) ====================

@api_router.get("/reports/scan/{scan_id}/pdf")
async def download_scan_report(scan_id: str, user: User = Depends(require_plan("premium"))):
    scan = await db.scans.find_one({"id": scan_id, "user_id": user.id}, {"_id": 0, "raw_results": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    iocs = await db.iocs.find({"scan_id": scan_id}, {"_id": 0}).to_list(100)
    user_info = {"email": user.email, "name": user.name}
    pdf_bytes = generate_scan_pdf(scan, iocs, user_info)
    return Response(content=pdf_bytes, media_type="application/pdf",
                   headers={"Content-Disposition": f"attachment; filename=scan_report_{scan_id[:8]}.pdf"})


@api_router.get("/reports/summary")
async def download_summary_report(period: str = "weekly", user: User = Depends(require_plan("premium"))):
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 7)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    scans = await db.scans.find(
        {"user_id": user.id, "created_at": {"$gte": since}}, {"_id": 0, "raw_results": 0}
    ).sort("created_at", -1).to_list(100)
    user_info = {"email": user.email, "name": user.name}
    pdf_bytes = generate_summary_pdf(scans, user_info, period)
    return Response(content=pdf_bytes, media_type="application/pdf",
                   headers={"Content-Disposition": f"attachment; filename={period}_report.pdf"})


@api_router.post("/reports/schedule")
async def create_report_schedule(data: ReportScheduleCreate, user: User = Depends(require_plan("premium"))):
    if data.frequency not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=400, detail="Frequency must be daily, weekly, or monthly")
    # Check existing
    existing = await db.report_schedules.find_one({"user_id": user.id})
    now = datetime.now(timezone.utc)
    delta = {"daily": timedelta(days=1), "weekly": timedelta(days=7), "monthly": timedelta(days=30)}
    next_send = now + delta.get(data.frequency, timedelta(days=7))

    if existing:
        await db.report_schedules.update_one(
            {"user_id": user.id},
            {"$set": {"frequency": data.frequency, "format": data.format, "next_send": next_send.isoformat(), "enabled": True}}
        )
    else:
        await db.report_schedules.insert_one({
            "id": str(uuid.uuid4()), "user_id": user.id,
            "frequency": data.frequency, "format": data.format,
            "last_sent": None, "next_send": next_send.isoformat(), "enabled": True
        })
    return {"message": f"Report schedule set to {data.frequency}", "next_send": next_send.isoformat()}


@api_router.get("/reports/schedule")
async def get_report_schedule(user: User = Depends(require_plan("premium"))):
    schedule = await db.report_schedules.find_one({"user_id": user.id}, {"_id": 0})
    if not schedule:
        return {"enabled": False}
    return schedule


@api_router.delete("/reports/schedule")
async def delete_report_schedule(user: User = Depends(require_plan("premium"))):
    await db.report_schedules.update_one({"user_id": user.id}, {"$set": {"enabled": False}})
    return {"message": "Report schedule disabled"}


@api_router.post("/reports/send-now")
async def send_report_now(user: User = Depends(require_plan("premium"))):
    scans = await db.scans.find(
        {"user_id": user.id}, {"_id": 0, "raw_results": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    user_info = {"email": user.email, "name": user.name}
    pdf_bytes = generate_summary_pdf(scans, user_info, "on-demand")
    result = await send_report_email(
        user.email, "Link Shield - Scan Report",
        "<h2>Your Link Shield Report</h2><p>Please find your scan summary attached.</p>",
        pdf_bytes, "linkshield_report.pdf"
    )
    if result["success"]:
        return {"message": "Report sent to your email"}
    return {"message": "Report generated but email delivery failed (SMTP not configured)", "error": result.get("error")}


# ==================== TEAMS (Enterprise) ====================

@api_router.post("/teams")
async def create_team(data: TeamCreate, user: User = Depends(require_plan("enterprise"))):
    existing = await db.teams.find_one({"owner_id": user.id})
    if existing:
        raise HTTPException(status_code=400, detail="You already have a team")
    team_id = str(uuid.uuid4())
    await db.teams.insert_one({
        "id": team_id, "name": data.name, "owner_id": user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    await db.team_members.insert_one({
        "id": str(uuid.uuid4()), "team_id": team_id, "user_id": user.id, "role": "owner"
    })
    return {"id": team_id, "name": data.name, "message": "Team created"}


@api_router.get("/teams/my")
async def get_my_team(user: User = Depends(require_plan("enterprise"))):
    team = await db.teams.find_one({"owner_id": user.id}, {"_id": 0})
    if not team:
        # Check if member of a team
        membership = await db.team_members.find_one({"user_id": user.id}, {"_id": 0})
        if membership:
            team = await db.teams.find_one({"id": membership["team_id"]}, {"_id": 0})
    if not team:
        return {"has_team": False}
    members = await db.team_members.find({"team_id": team["id"]}, {"_id": 0}).to_list(100)
    # Enrich with user info
    for m in members:
        u = await db.users.find_one({"id": m["user_id"]}, {"_id": 0, "password_hash": 0, "api_key": 0})
        if u:
            m["user_info"] = {"name": u.get("name"), "email": u.get("email"), "username": u.get("username")}
    team["members"] = members
    team["has_team"] = True
    return team


@api_router.post("/teams/members")
async def add_team_member(data: TeamMemberAdd, user: User = Depends(require_plan("enterprise"))):
    team = await db.teams.find_one({"owner_id": user.id})
    if not team:
        raise HTTPException(status_code=404, detail="You don't have a team")
    # Check member limit
    member_count = await db.team_members.count_documents({"team_id": team["id"]})
    if member_count >= PLAN_CONFIG["enterprise"]["max_team_members"]:
        raise HTTPException(status_code=400, detail="Team member limit reached")
    # Find user by email
    target = await db.users.find_one({"email": data.email})
    if not target:
        raise HTTPException(status_code=404, detail="User not found with that email")
    existing = await db.team_members.find_one({"team_id": team["id"], "user_id": target["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="User already in team")
    await db.team_members.insert_one({
        "id": str(uuid.uuid4()), "team_id": team["id"], "user_id": target["id"], "role": data.role
    })
    await create_notification(target["id"], "team_invite", f"You've been added to team '{team['name']}'")
    return {"message": f"{data.email} added to team"}


@api_router.delete("/teams/members/{member_user_id}")
async def remove_team_member(member_user_id: str, user: User = Depends(require_plan("enterprise"))):
    team = await db.teams.find_one({"owner_id": user.id})
    if not team:
        raise HTTPException(status_code=404, detail="You don't have a team")
    if member_user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from your own team")
    result = await db.team_members.delete_one({"team_id": team["id"], "user_id": member_user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member removed"}


# ==================== WEBHOOKS (Enterprise) ====================

@api_router.post("/webhooks")
async def create_webhook(data: WebhookCreate, user: User = Depends(require_plan("enterprise"))):
    webhook_count = await db.webhooks.count_documents({"user_id": user.id})
    if webhook_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 webhooks allowed")
    valid_events = ["scan.completed", "scan.failed", "credits.low", "team.member_added"]
    for event in data.events:
        if event not in valid_events:
            raise HTTPException(status_code=400, detail=f"Invalid event: {event}. Valid: {valid_events}")
    webhook_id = str(uuid.uuid4())
    secret = data.secret or secrets.token_hex(32)
    await db.webhooks.insert_one({
        "id": webhook_id, "user_id": user.id, "url": data.url,
        "events": data.events, "secret": secret, "enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"id": webhook_id, "secret": secret, "message": "Webhook created"}


@api_router.get("/webhooks")
async def list_webhooks(user: User = Depends(require_plan("enterprise"))):
    webhooks = await db.webhooks.find({"user_id": user.id}, {"_id": 0}).to_list(20)
    for wh in webhooks:
        wh["secret"] = mask_key(wh.get("secret", ""))
        deliveries = await db.webhook_deliveries.find(
            {"webhook_id": wh["id"]}, {"_id": 0}
        ).sort("created_at", -1).limit(5).to_list(5)
        wh["recent_deliveries"] = deliveries
    return webhooks


@api_router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, user: User = Depends(require_plan("enterprise"))):
    result = await db.webhooks.delete_one({"id": webhook_id, "user_id": user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted"}


@api_router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str, user: User = Depends(require_plan("enterprise"))):
    webhook = await db.webhooks.find_one({"id": webhook_id, "user_id": user.id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    from services.webhooks import deliver_webhook
    result = await deliver_webhook(webhook, "test.ping", {"message": "Test ping from Link Shield", "timestamp": datetime.now(timezone.utc).isoformat()}, db)
    return {"success": result.get("success"), "status_code": result.get("response_status"), "error": result.get("error")}


# ==================== ADMIN ROUTES ====================

@api_router.get("/admin/users")
async def admin_get_users(search: Optional[str] = None, user: User = Depends(get_admin_user)):
    query = {}
    if search:
        query = {"$or": [
            {"email": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
            {"username": {"$regex": search, "$options": "i"}}
        ]}
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(200)
    return users


@api_router.put("/admin/users/{user_id}/plan")
async def update_user_plan(user_id: str, data: UpdatePlanRequest, current_user: User = Depends(get_owner_user)):
    if data.plan not in PLAN_CONFIG:
        raise HTTPException(status_code=400, detail="Invalid plan")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    old_plan = target["plan"]
    new_credits = PLAN_CONFIG[data.plan]["credits_per_month"]
    await db.users.update_one({"id": user_id}, {"$set": {"plan": data.plan, "credits": new_credits}})
    await create_audit_log("plan_changed", current_user.id, user_id, f"Plan: {old_plan} -> {data.plan}")
    await create_notification(user_id, "plan_changed", f"Your plan has been updated to {data.plan.upper()}")
    return {"message": "Plan updated", "new_plan": data.plan, "new_credits": new_credits}


@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(user_id: str, data: UpdateRoleRequest, current_user: User = Depends(get_admin_user)):
    if data.role not in ("user", "admin", "owner"):
        raise HTTPException(status_code=400, detail="Invalid role")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "owner" and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Cannot modify owner")
    if data.role in ("admin", "owner") and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can promote")
    await db.users.update_one({"id": user_id}, {"$set": {"role": data.role}})
    await create_audit_log("role_changed", current_user.id, user_id, f"Role changed to {data.role}")
    return {"message": "Role updated"}


@api_router.post("/admin/users/{user_id}/add-credits")
async def add_credits(user_id: str, data: CreditAdjust, user: User = Depends(get_admin_user)):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$inc": {"credits": data.amount}})
    await db.credit_history.insert_one({
        "user_id": user_id, "amount": data.amount, "reason": data.reason,
        "admin_id": user.id, "timestamp": datetime.now(timezone.utc).isoformat()
    })
    await create_audit_log("credits_added", user.id, user_id, f"+{data.amount} credits: {data.reason}")
    return {"message": f"Added {data.amount} credits"}


@api_router.post("/admin/users/{user_id}/deduct-credits")
async def deduct_credits(user_id: str, data: CreditAdjust, user: User = Depends(get_admin_user)):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["credits"] < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient credits to deduct")
    await db.users.update_one({"id": user_id}, {"$inc": {"credits": -data.amount}})
    await db.credit_history.insert_one({
        "user_id": user_id, "amount": -data.amount, "reason": data.reason,
        "admin_id": user.id, "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"message": f"Deducted {data.amount} credits"}


@api_router.post("/admin/users/{user_id}/reset-credits")
async def reset_credits(user_id: str, user: User = Depends(get_admin_user)):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    default = PLAN_CONFIG.get(target["plan"], PLAN_CONFIG["free"])["credits_per_month"]
    await db.users.update_one({"id": user_id}, {"$set": {"credits": default}})
    return {"message": f"Credits reset to {default}"}


@api_router.put("/admin/users/{user_id}/status")
async def update_user_status(user_id: str, status: dict, user: User = Depends(get_admin_user)):
    new_status = status.get("status", "active")
    await db.users.update_one({"id": user_id}, {"$set": {"status": new_status}})
    return {"message": f"User {new_status}"}


@api_router.get("/admin/analytics/detailed")
async def admin_analytics(user: User = Depends(get_admin_user)):
    total_users = await db.users.count_documents({})
    total_scans = await db.scans.count_documents({})
    premium_users = await db.users.count_documents({"plan": "premium"})
    enterprise_users = await db.users.count_documents({"plan": "enterprise"})
    free_users = await db.users.count_documents({"plan": "free"})
    active_users = await db.users.count_documents({"status": {"$ne": "suspended"}})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scans_today = await db.scans.count_documents({"created_at": {"$regex": f"^{today}"}})
    queue_stats = await get_queue_stats()
    return {
        "total_users": total_users, "total_scans": total_scans,
        "premium_users": premium_users, "enterprise_users": enterprise_users,
        "free_users": free_users, "active_users": active_users,
        "scans_today": scans_today, "queue_stats": queue_stats
    }


@api_router.get("/admin/scans")
async def admin_get_scans(limit: int = 50, user: User = Depends(get_admin_user)):
    scans = await db.scans.find({}, {"_id": 0, "raw_results": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    for scan in scans:
        u = await db.users.find_one({"id": scan.get("user_id")}, {"_id": 0, "email": 1, "name": 1})
        scan["user_info"] = u
    return scans


# ==================== OWNER ROUTES ====================

@api_router.post("/owner/create-admin")
async def create_admin(data: CreateAdminRequest, current_user: User = Depends(get_owner_user)):
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    username = re.sub(r'[^a-z0-9_]', '', data.email.split('@')[0].lower())[:20]
    existing_un = await db.users.find_one({"username": username})
    counter = 1
    base = username
    while existing_un:
        username = f"{base}{counter}"[:20]
        existing_un = await db.users.find_one({"username": username})
        counter += 1
    user_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": user_id, "email": data.email, "username": username,
        "name": data.name, "password_hash": hash_password(data.temporary_password),
        "role": "admin", "plan": "premium", "credits": 1000,
        "api_key": None, "api_call_count": 0,
        "api_call_reset": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    await create_audit_log("admin_created", current_user.id, user_id, f"Admin created: {data.email}")
    return {"message": "Admin created", "user_id": user_id, "username": username}


@api_router.get("/owner/admins")
async def get_admins(current_user: User = Depends(get_owner_user)):
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "password_hash": 0, "api_key": 0}).to_list(100)
    return admins


@api_router.get("/owner/audit-logs")
async def get_audit_logs(limit: int = 100, action_type: Optional[str] = None, current_user: User = Depends(get_owner_user)):
    query = {}
    if action_type:
        query["action_type"] = action_type
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    for log in logs:
        if log.get("performed_by"):
            performer = await db.users.find_one({"id": log["performed_by"]}, {"_id": 0, "email": 1, "name": 1, "username": 1, "role": 1})
            if performer:
                log["performed_by_info"] = performer
        if log.get("target_user"):
            target = await db.users.find_one({"id": log["target_user"]}, {"_id": 0, "email": 1, "name": 1, "username": 1, "role": 1})
            if target:
                log["target_user_info"] = target
    return logs


# ==================== OWNER: PRICING & SETTINGS ====================

@api_router.get("/owner/site-settings")
async def get_site_settings(current_user: User = Depends(get_owner_user)):
    settings = {}
    cursor = db.site_settings.find({}, {"_id": 0})
    async for doc in cursor:
        settings[doc["key"]] = doc["value"]
    # Set defaults if not exist
    if "premium_price" not in settings:
        settings["premium_price"] = "499"
    if "enterprise_price" not in settings:
        settings["enterprise_price"] = "2499"
    return settings


@api_router.put("/owner/site-settings/prices")
async def update_prices(data: PriceUpdate, current_user: User = Depends(get_owner_user)):
    if data.premium_price < 0 or data.enterprise_price < 0:
        raise HTTPException(status_code=400, detail="Prices must be non-negative")
    for key, value in [("premium_price", str(data.premium_price)), ("enterprise_price", str(data.enterprise_price))]:
        await db.site_settings.update_one(
            {"key": key},
            {"$set": {"key": key, "value": value, "updated_by": current_user.id, "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
    await create_audit_log("prices_updated", current_user.id, details=f"Premium: {data.premium_price}, Enterprise: {data.enterprise_price}")
    return {"message": "Prices updated", "premium_price": data.premium_price, "enterprise_price": data.enterprise_price}


@api_router.get("/owner/payment-settings")
async def get_payment_settings(current_user: User = Depends(get_owner_user)):
    settings = await db.payment_settings.find_one({"_id": "razorpay"})
    default_key_id = os.environ.get("RAZORPAY_KEY_ID", "")
    default_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
    if settings:
        return {
            "gateway": "razorpay",
            "key_id": settings.get("key_id", ""),
            "key_secret_masked": mask_key(decrypt_value(settings["key_secret_encrypted"])) if settings.get("key_secret_encrypted") else "",
            "is_active": settings.get("is_active", True),
            "updated_at": settings.get("updated_at", "")
        }
    return {
        "gateway": "razorpay",
        "key_id": default_key_id,
        "key_secret_masked": mask_key(default_secret) if default_secret else "",
        "is_active": True,
        "is_default": True
    }


@api_router.put("/owner/payment-settings")
async def update_payment_settings(data: PaymentSettingsUpdate, current_user: User = Depends(get_owner_user)):
    if not data.key_id or not data.key_secret:
        raise HTTPException(status_code=400, detail="Key ID and Secret required")
    await db.payment_settings.update_one(
        {"_id": "razorpay"},
        {"$set": {
            "gateway": "razorpay", "key_id": data.key_id,
            "key_secret_encrypted": encrypt_value(data.key_secret),
            "is_active": data.is_active,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user.id
        }},
        upsert=True
    )
    await create_audit_log("payment_settings_updated", current_user.id, details=f"Gateway updated: {mask_key(data.key_id)}")
    return {"message": "Payment settings updated"}


# ==================== PLANS & BILLING ====================

@api_router.get("/billing/plans")
async def get_plans():
    # Load dynamic pricing
    premium_price = 499
    enterprise_price = 2499
    settings = await db.site_settings.find_one({"key": "premium_price"})
    if settings:
        premium_price = int(settings["value"])
    settings = await db.site_settings.find_one({"key": "enterprise_price"})
    if settings:
        enterprise_price = int(settings["value"])

    return [
        {
            "name": "free", "price": 0,
            "features": ["50 credits/month", "URL & File scanning", "Basic risk scoring", "URLhaus + VirusTotal", "Scan history"],
            "limits": PLAN_CONFIG["free"]
        },
        {
            "name": "premium", "price": premium_price,
            "features": [
                "500 credits/month", "Priority queue scanning", "Full scanner suite (VT + urlscan.io + URLhaus + MalwareBazaar)",
                "IOC extraction & export (CSV/JSON)", "API key access (1000 calls/day)", "PDF scan reports",
                "Email report scheduling", "Advanced threat intelligence"
            ],
            "limits": PLAN_CONFIG["premium"]
        },
        {
            "name": "enterprise", "price": enterprise_price,
            "features": [
                "Unlimited credits", "Highest priority scanning", "All Premium features",
                "API access (10,000 calls/day)", "Team workspace (up to 50 members)",
                "Webhooks (real-time notifications)", "Custom report scheduling",
                "Dedicated support"
            ],
            "limits": PLAN_CONFIG["enterprise"]
        }
    ]


@api_router.get("/user/stats")
async def get_user_stats(user: User = Depends(get_current_user)):
    total_scans = await db.scans.count_documents({"user_id": user.id})
    user_doc = await db.users.find_one({"id": user.id}, {"_id": 0, "password_hash": 0})
    plan_config = PLAN_CONFIG.get(user.plan, PLAN_CONFIG["free"])
    recent_scans = await db.scans.find(
        {"user_id": user.id}, {"_id": 0, "raw_results": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    return {
        "total_scans": total_scans, "credits": user_doc.get("credits", 0),
        "plan": user.plan, "plan_features": plan_config,
        "recent_scans": recent_scans,
        "has_api_key": bool(user_doc.get("api_key"))
    }


@api_router.get("/user/notifications")
async def get_notifications(user: User = Depends(get_current_user)):
    notifs = await db.notifications.find(
        {"user_id": user.id}, {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    return notifs


@api_router.put("/user/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, user: User = Depends(get_current_user)):
    await db.notifications.update_one({"id": notif_id, "user_id": user.id}, {"$set": {"read": True}})
    return {"message": "Marked as read"}


# ==================== SETUP ====================

app.include_router(api_router)

# Enterprise + Network Scanner routes
_enterprise_router, _owner_verif_router = _build_enterprise_routes(db, get_current_user, get_owner_user, fernet)
app.include_router(_enterprise_router)
app.include_router(_owner_verif_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    # Ensure indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.users.create_index("api_key", sparse=True)
    await db.scans.create_index([("user_id", 1), ("created_at", -1)])
    await db.iocs.create_index("scan_id")
    await db.webhooks.create_index("user_id")
    await db.team_members.create_index("team_id")
    # Seed default site settings
    existing = await db.site_settings.find_one({"key": "premium_price"})
    if not existing:
        await db.site_settings.insert_many([
            {"key": "premium_price", "value": "499", "updated_at": datetime.now(timezone.utc).isoformat()},
            {"key": "enterprise_price", "value": "2499", "updated_at": datetime.now(timezone.utc).isoformat()}
        ])
    logger.info("Link Shield API started")


@app.on_event("shutdown")
async def shutdown():
    client.close()
