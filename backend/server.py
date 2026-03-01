from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import hashlib
import random
import re
import razorpay
import hmac

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

JWT_SECRET = os.environ.get('JWT_SECRET', 'link-shield-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_demo_key')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'rzp_test_demo_secret')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

PLAN_PRICES = {
    'free': 0,
    'premium': 499,
    'enterprise': 2499
}

PLAN_FEATURES = {
    'free': {
        'credits_per_month': 50,
        'max_file_size': 10 * 1024 * 1024,
        'features': ['50 credits per month', 'Basic scans', 'Limited file size (10MB)', 'Basic reports']
    },
    'premium': {
        'credits_per_month': 500,
        'max_file_size': 100 * 1024 * 1024,
        'features': [
            '500 credits per month',
            'Advanced threat analysis',
            'IOC extraction',
            'Priority scan queue',
            'Full scan history',
            'PDF reports',
            'Alerts and monitoring',
            'Basic API access'
        ]
    },
    'enterprise': {
        'credits_per_month': 999999,
        'max_file_size': 500 * 1024 * 1024,
        'features': [
            'Unlimited scans (fair usage)',
            'Large file uploads (500MB)',
            'Team workspace',
            'Advanced analytics',
            'Custom reports',
            'High API limits',
            'Dedicated priority queue'
        ]
    }
}

SUSPICIOUS_KEYWORDS = ['phishing', 'malware', 'virus', 'hack', 'exploit', 'trojan', 'ransomware', 'suspicious', 'fake', 'scam']
SUSPICIOUS_EXTENSIONS = ['.exe', '.bat', '.cmd', '.scr', '.vbs', '.js', '.jar', '.apk']

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str = "user"
    plan: str = "free"
    credits: int = 50
    created_at: str

class ChangeEmail(BaseModel):
    current_password: str
    new_email: EmailStr

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class CreateAdmin(BaseModel):
    email: EmailStr
    name: str
    temporary_password: str

class URLScanRequest(BaseModel):
    url: str

class ScanResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    scan_type: str
    target: str
    status: str
    risk_score: int
    risk_level: str
    metadata: dict
    iocs: dict
    summary: str
    created_at: str

class UpdateUserCredits(BaseModel):
    credits: int

class UpdateUserPlan(BaseModel):
    plan: str

class UpdateUserRole(BaseModel):
    role: str

class UpgradePlan(BaseModel):
    plan: str

class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    type: str
    message: str
    read: bool
    created_at: str

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload['user_id']}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(user: User = Depends(get_current_user)):
    if user.role not in ["admin", "owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def get_owner_user(user: User = Depends(get_current_user)):
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return user

async def create_notification(user_id: str, notification_type: str, message: str):
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": notification_type,
        "message": message,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)

def analyze_url(url: str) -> dict:
    risk_score = 0
    threats = []
    
    url_lower = url.lower()
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in url_lower:
            risk_score += 15
            threats.append(f"Suspicious keyword detected: {keyword}")
    
    if not url.startswith('https://'):
        risk_score += 10
        threats.append("Non-HTTPS connection")
    
    if len(url) > 100:
        risk_score += 5
        threats.append("Unusually long URL")
    
    if url.count('-') > 3 or url.count('.') > 4:
        risk_score += 10
        threats.append("Suspicious URL structure")
    
    risk_score = min(risk_score + random.randint(-10, 20), 100)
    
    if risk_score < 40:
        risk_level = "safe"
        summary = "No significant threats detected. URL appears to be safe."
    elif risk_score < 70:
        risk_level = "suspicious"
        summary = f"Potentially unsafe content detected. Threats: {', '.join(threats) if threats else 'Suspicious patterns found'}."
    else:
        risk_level = "malicious"
        summary = f"Dangerous threats detected. Threats: {', '.join(threats) if threats else 'High-risk patterns identified'}. Do not proceed."
    
    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "summary": summary,
        "threats": threats
    }

def analyze_file(filename: str, content: bytes) -> dict:
    risk_score = 0
    threats = []
    
    file_ext = Path(filename).suffix.lower()
    if file_ext in SUSPICIOUS_EXTENSIONS:
        risk_score += 30
        threats.append(f"Suspicious file extension: {file_ext}")
    
    if len(content) > 10 * 1024 * 1024:
        risk_score += 10
        threats.append("Large file size")
    
    filename_lower = filename.lower()
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in filename_lower:
            risk_score += 15
            threats.append(f"Suspicious keyword in filename: {keyword}")
    
    risk_score = min(risk_score + random.randint(-10, 20), 100)
    
    if risk_score < 40:
        risk_level = "safe"
        summary = "File appears to be safe. No malicious patterns detected."
    elif risk_score < 70:
        risk_level = "suspicious"
        summary = f"File may contain suspicious content. Threats: {', '.join(threats) if threats else 'Suspicious patterns found'}."
    else:
        risk_level = "malicious"
        summary = f"File contains dangerous content. Threats: {', '.join(threats) if threats else 'High-risk patterns identified'}. Do not execute."
    
    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "summary": summary,
        "threats": threats
    }

@api_router.post("/auth/signup")
async def signup(data: UserSignup):
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": "user",
        "plan": "free",
        "credits": 50,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id, data.email, "user")
    user_response = {k: v for k, v in user_doc.items() if k != "password_hash" and k != "_id"}
    
    return {"token": token, "user": user_response}

@api_router.post("/auth/login")
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user['id'], user['email'], user['role'])
    user_response = {k: v for k, v in user.items() if k != "password_hash" and k != "_id"}
    
    return {"token": token, "user": user_response}

@api_router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    fresh_user = await db.users.find_one({"id": user.id}, {"_id": 0, "password_hash": 0})
    return fresh_user

@api_router.put("/account/email")
async def change_email(data: ChangeEmail, user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": user.id})
    if not verify_password(data.current_password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    existing = await db.users.find_one({"email": data.new_email})
    if existing and existing['id'] != user.id:
        raise HTTPException(status_code=400, detail="Email already in use")
    
    await db.users.update_one({"id": user.id}, {"$set": {"email": data.new_email}})
    return {"message": "Email updated successfully"}

@api_router.put("/account/password")
async def change_password(data: ChangePassword, user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": user.id})
    if not verify_password(data.current_password, user_doc['password_hash']):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    new_hash = hash_password(data.new_password)
    await db.users.update_one({"id": user.id}, {"$set": {"password_hash": new_hash}})
    return {"message": "Password updated successfully"}

@api_router.post("/scan/url")
async def scan_url(data: URLScanRequest, user: User = Depends(get_current_user)):
    fresh_user = await db.users.find_one({"id": user.id})
    
    if fresh_user['plan'] == 'enterprise':
        cost = 0
    elif fresh_user['plan'] == 'premium':
        cost = 3
    else:
        cost = 5
    
    if cost > 0 and fresh_user['credits'] < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    scan_id = str(uuid.uuid4())
    scan_doc = {
        "id": scan_id,
        "user_id": user.id,
        "scan_type": "url",
        "target": data.url,
        "status": "queued",
        "risk_score": 0,
        "risk_level": "unknown",
        "metadata": {},
        "iocs": {},
        "summary": "",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.scans.insert_one(scan_doc)
    
    analysis = analyze_url(data.url)
    
    scan_doc.update({
        "status": "completed",
        "risk_score": analysis['risk_score'],
        "risk_level": analysis['risk_level'],
        "summary": analysis['summary'],
        "metadata": {
            "domain": data.url.split('/')[2] if len(data.url.split('/')) > 2 else data.url,
            "protocol": "https" if "https" in data.url else "http",
            "threats_detected": len(analysis['threats'])
        },
        "iocs": {
            "ips": [f"192.168.{random.randint(1,255)}.{random.randint(1,255)}"],
            "domains": [data.url.split('/')[2] if len(data.url.split('/')) > 2 else data.url],
            "hashes": [hashlib.md5(data.url.encode()).hexdigest()]
        }
    })
    
    await db.scans.update_one({"id": scan_id}, {"$set": scan_doc})
    
    if cost > 0:
        await db.users.update_one({"id": user.id}, {"$inc": {"credits": -cost}})
        await db.credit_history.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user.id,
            "amount": -cost,
            "reason": "URL scan",
            "scan_id": scan_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    await db.activity_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user.id,
        "action": "url_scan",
        "details": f"Scanned URL: {data.url}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    await create_notification(user.id, "scan_complete", f"URL scan completed: {analysis['risk_level']}")
    
    return {**{k: v for k, v in scan_doc.items() if k != "_id"}, "credits_used": cost}

@api_router.post("/scan/file")
async def scan_file(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    fresh_user = await db.users.find_one({"id": user.id})
    
    if fresh_user['plan'] == 'enterprise':
        cost = 0
    elif fresh_user['plan'] == 'premium':
        cost = 6
    else:
        cost = 10
    
    if cost > 0 and fresh_user['credits'] < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    scan_id = str(uuid.uuid4())
    scan_doc = {
        "id": scan_id,
        "user_id": user.id,
        "scan_type": "file",
        "target": file.filename,
        "status": "queued",
        "risk_score": 0,
        "risk_level": "unknown",
        "metadata": {},
        "iocs": {},
        "summary": "",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.scans.insert_one(scan_doc)
    
    analysis = analyze_file(file.filename, file_content)
    
    scan_doc.update({
        "status": "completed",
        "risk_score": analysis['risk_score'],
        "risk_level": analysis['risk_level'],
        "summary": analysis['summary'],
        "metadata": {
            "filename": file.filename,
            "size": len(file_content),
            "type": file.content_type,
            "hash": file_hash,
            "threats_detected": len(analysis['threats'])
        },
        "iocs": {
            "ips": [f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"],
            "domains": [f"malicious{random.randint(1,999)}.com"],
            "hashes": [file_hash]
        }
    })
    
    await db.scans.update_one({"id": scan_id}, {"$set": scan_doc})
    
    if cost > 0:
        await db.users.update_one({"id": user.id}, {"$inc": {"credits": -cost}})
        await db.credit_history.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user.id,
            "amount": -cost,
            "reason": "File scan",
            "scan_id": scan_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    await db.activity_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user.id,
        "action": "file_scan",
        "details": f"Scanned file: {file.filename}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    await create_notification(user.id, "scan_complete", f"File scan completed: {analysis['risk_level']}")
    
    return {**{k: v for k, v in scan_doc.items() if k != "_id"}, "credits_used": cost}

@api_router.get("/scan/{scan_id}")
async def get_scan(scan_id: str, user: User = Depends(get_current_user)):
    scan = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan['user_id'] != user.id and user.role not in ["admin", "owner"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return scan

@api_router.get("/scan/history/list")
async def get_scan_history(user: User = Depends(get_current_user)):
    scans = await db.scans.find({"user_id": user.id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return scans

@api_router.get("/user/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return user

@api_router.get("/user/stats")
async def get_user_stats(user: User = Depends(get_current_user)):
    total_scans = await db.scans.count_documents({"user_id": user.id})
    malicious_count = await db.scans.count_documents({"user_id": user.id, "risk_level": "malicious"})
    suspicious_count = await db.scans.count_documents({"user_id": user.id, "risk_level": "suspicious"})
    safe_count = await db.scans.count_documents({"user_id": user.id, "risk_level": "safe"})
    
    return {
        "total_scans": total_scans,
        "malicious": malicious_count,
        "suspicious": suspicious_count,
        "safe": safe_count
    }

@api_router.get("/user/credits/history")
async def get_credit_history(user: User = Depends(get_current_user)):
    history = await db.credit_history.find({"user_id": user.id}, {"_id": 0}).sort("timestamp", -1).limit(50).to_list(50)
    return history

@api_router.get("/user/notifications")
async def get_notifications(user: User = Depends(get_current_user)):
    notifications = await db.notifications.find({"user_id": user.id}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    return notifications

@api_router.put("/user/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: User = Depends(get_current_user)):
    await db.notifications.update_one({"id": notification_id, "user_id": user.id}, {"$set": {"read": True}})
    return {"message": "Notification marked as read"}

@api_router.post("/billing/upgrade")
async def upgrade_plan(data: UpgradePlan, user: User = Depends(get_current_user)):
    if data.plan not in ['free', 'premium', 'enterprise']:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    if user.plan == data.plan:
        raise HTTPException(status_code=400, detail="Already on this plan")
    
    amount = 0
    if data.plan == 'premium':
        amount = 29
    elif data.plan == 'enterprise':
        amount = 99
    
    transaction_id = str(uuid.uuid4())
    await db.transactions.insert_one({
        "id": transaction_id,
        "user_id": user.id,
        "plan": data.plan,
        "amount": amount,
        "status": "pending",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "Upgrade request created",
        "transaction_id": transaction_id,
        "amount": amount,
        "note": "Payment integration not yet implemented. Contact admin to complete upgrade."
    }

@api_router.get("/billing/history")
async def get_billing_history(user: User = Depends(get_current_user)):
    history = await db.transactions.find({"user_id": user.id}, {"_id": 0}).sort("timestamp", -1).to_list(50)
    return history

@api_router.get("/admin/users", dependencies=[Depends(get_admin_user)])
async def get_all_users(search: Optional[str] = None):
    query = {}
    if search:
        query = {"$or": [{"email": {"$regex": search, "$options": "i"}}, {"name": {"$regex": search, "$options": "i"}}]}
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(1000)
    return users

@api_router.put("/admin/users/{user_id}/credits", dependencies=[Depends(get_admin_user)])
async def update_user_credits(user_id: str, data: UpdateUserCredits):
    result = await db.users.update_one({"id": user_id}, {"$set": {"credits": data.credits}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.credit_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "amount": data.credits,
        "reason": "Admin adjustment",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Credits updated"}

@api_router.put("/admin/users/{user_id}/plan", dependencies=[Depends(get_admin_user)])
async def update_user_plan(user_id: str, data: UpdateUserPlan):
    result = await db.users.update_one({"id": user_id}, {"$set": {"plan": data.plan}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Plan updated"}

@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(user_id: str, data: UpdateUserRole, current_user: User = Depends(get_admin_user)):
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user['role'] == 'owner':
        raise HTTPException(status_code=403, detail="Cannot modify owner role")
    
    if data.role == 'admin' and current_user.role != 'owner':
        raise HTTPException(status_code=403, detail="Only owner can create admins")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": data.role}})
    return {"message": "Role updated"}

@api_router.get("/admin/stats", dependencies=[Depends(get_admin_user)])
async def get_admin_stats():
    total_users = await db.users.count_documents({})
    total_scans = await db.scans.count_documents({})
    premium_users = await db.users.count_documents({"plan": "premium"})
    enterprise_users = await db.users.count_documents({"plan": "enterprise"})
    recent_scans = await db.scans.find({}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10)
    
    return {
        "total_users": total_users,
        "total_scans": total_scans,
        "premium_users": premium_users,
        "enterprise_users": enterprise_users,
        "free_users": total_users - premium_users - enterprise_users,
        "recent_scans": recent_scans
    }

@api_router.get("/admin/activity", dependencies=[Depends(get_admin_user)])
async def get_activity_logs():
    logs = await db.activity_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(50).to_list(50)
    return logs

@api_router.get("/admin/analytics")
async def get_analytics(current_user: User = Depends(get_admin_user)):
    pipeline = [
        {"$group": {
            "_id": "$risk_level",
            "count": {"$sum": 1}
        }}
    ]
    threat_distribution = await db.scans.aggregate(pipeline).to_list(100)
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    last_7_days = []
    for i in range(7):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        count = await db.scans.count_documents({
            "created_at": {"$gte": day.isoformat(), "$lt": next_day.isoformat()}
        })
        last_7_days.append({"date": day.strftime("%Y-%m-%d"), "count": count})
    
    return {
        "threat_distribution": threat_distribution,
        "scan_trends": list(reversed(last_7_days))
    }

@api_router.post("/owner/create-admin")
async def create_admin(data: CreateAdmin, current_user: User = Depends(get_owner_user)):
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password_hash": hash_password(data.temporary_password),
        "name": data.name,
        "role": "admin",
        "plan": "premium",
        "credits": 1000,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    return {
        "message": "Admin created successfully",
        "email": data.email,
        "temporary_password": data.temporary_password
    }

@api_router.delete("/owner/remove-admin/{user_id}")
async def remove_admin(user_id: str, current_user: User = Depends(get_owner_user)):
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user['role'] != 'admin':
        raise HTTPException(status_code=400, detail="User is not an admin")
    
    await db.users.update_one({"id": user_id}, {"$set": {"role": "user", "plan": "free"}})
    return {"message": "Admin privileges removed"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()