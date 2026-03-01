from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status
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
    created_at: str

class UpdateUserCredits(BaseModel):
    credits: int

class UpdateUserPlan(BaseModel):
    plan: str

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
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

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
    return user

@api_router.post("/scan/url")
async def scan_url(data: URLScanRequest, user: User = Depends(get_current_user)):
    cost = 5 if user.plan == "free" else 3
    
    if user.credits < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    risk_score = random.randint(0, 100)
    if risk_score < 40:
        risk_level = "safe"
    elif risk_score < 70:
        risk_level = "suspicious"
    else:
        risk_level = "malicious"
    
    scan_id = str(uuid.uuid4())
    scan_doc = {
        "id": scan_id,
        "user_id": user.id,
        "scan_type": "url",
        "target": data.url,
        "status": "completed",
        "risk_score": risk_score,
        "risk_level": risk_level,
        "metadata": {
            "domain": data.url.split('/')[2] if len(data.url.split('/')) > 2 else data.url,
            "protocol": "https" if "https" in data.url else "http"
        },
        "iocs": {
            "ips": [f"192.168.{random.randint(1,255)}.{random.randint(1,255)}"],
            "domains": [data.url.split('/')[2] if len(data.url.split('/')) > 2 else data.url],
            "hashes": [hashlib.md5(data.url.encode()).hexdigest()]
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.scans.insert_one(scan_doc)
    await db.users.update_one({"id": user.id}, {"$inc": {"credits": -cost}})
    
    await db.activity_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user.id,
        "action": "url_scan",
        "details": f"Scanned URL: {data.url}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {**{k: v for k, v in scan_doc.items() if k != "_id"}, "credits_used": cost}

@api_router.post("/scan/file")
async def scan_file(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    cost = 10 if user.plan == "free" else 6
    
    if user.credits < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    risk_score = random.randint(0, 100)
    if risk_score < 40:
        risk_level = "safe"
    elif risk_score < 70:
        risk_level = "suspicious"
    else:
        risk_level = "malicious"
    
    scan_id = str(uuid.uuid4())
    scan_doc = {
        "id": scan_id,
        "user_id": user.id,
        "scan_type": "file",
        "target": file.filename,
        "status": "completed",
        "risk_score": risk_score,
        "risk_level": risk_level,
        "metadata": {
            "filename": file.filename,
            "size": len(file_content),
            "type": file.content_type,
            "hash": file_hash
        },
        "iocs": {
            "ips": [f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"],
            "domains": [f"malicious{random.randint(1,999)}.com"],
            "hashes": [file_hash]
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.scans.insert_one(scan_doc)
    await db.users.update_one({"id": user.id}, {"$inc": {"credits": -cost}})
    
    await db.activity_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user.id,
        "action": "file_scan",
        "details": f"Scanned file: {file.filename}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {**{k: v for k, v in scan_doc.items() if k != "_id"}, "credits_used": cost}

@api_router.get("/scan/{scan_id}")
async def get_scan(scan_id: str, user: User = Depends(get_current_user)):
    scan = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan['user_id'] != user.id and user.role != "admin":
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

@api_router.get("/admin/users", dependencies=[Depends(get_admin_user)])
async def get_all_users():
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return users

@api_router.put("/admin/users/{user_id}/credits", dependencies=[Depends(get_admin_user)])
async def update_user_credits(user_id: str, data: UpdateUserCredits):
    result = await db.users.update_one({"id": user_id}, {"$set": {"credits": data.credits}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Credits updated"}

@api_router.put("/admin/users/{user_id}/plan", dependencies=[Depends(get_admin_user)])
async def update_user_plan(user_id: str, data: UpdateUserPlan):
    result = await db.users.update_one({"id": user_id}, {"$set": {"plan": data.plan}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Plan updated"}

@api_router.get("/admin/stats", dependencies=[Depends(get_admin_user)])
async def get_admin_stats():
    total_users = await db.users.count_documents({})
    total_scans = await db.scans.count_documents({})
    premium_users = await db.users.count_documents({"plan": "premium"})
    recent_scans = await db.scans.find({}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10)
    
    return {
        "total_users": total_users,
        "total_scans": total_scans,
        "premium_users": premium_users,
        "free_users": total_users - premium_users,
        "recent_scans": recent_scans
    }

@api_router.get("/admin/activity", dependencies=[Depends(get_admin_user)])
async def get_activity_logs():
    logs = await db.activity_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(50).to_list(50)
    return logs

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