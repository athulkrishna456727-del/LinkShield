"""Enterprise verification + Network Scanner endpoints."""
import asyncio
import io
import json
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "verification"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".heic"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])
owner_router = APIRouter(prefix="/api/owner/verification", tags=["owner_verification"])


# ---------- MODELS ----------

class StartScanRequest(BaseModel):
    ip_ranges: list[str]
    ports: Optional[str] = None
    protocols: Optional[list[str]] = None
    credentials_used: bool = False  # informational only - we never store creds


class VerificationDecision(BaseModel):
    notes: Optional[str] = ""
    auto_send_email: bool = False


# ---------- HELPERS ----------

def _safe_ext(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")
    return ext


async def _save_upload(upload: UploadFile, prefix: str) -> tuple[str, int]:
    ext = _safe_ext(upload.filename)
    data = await upload.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"{prefix}: file exceeds 10MB")
    fname = f"{prefix}_{uuid.uuid4().hex}{ext}"
    fpath = UPLOAD_DIR / fname
    fpath.write_bytes(data)
    return str(fpath), len(data)


def _extract_company_from_letter(file_path: str) -> Optional[str]:
    """Best-effort extract company domain from auth letter (PDF text or filename)."""
    try:
        if file_path.lower().endswith(".pdf"):
            from pypdf import PdfReader  # type: ignore
            try:
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages[:3]:
                    text += page.extract_text() or ""
                m = re.search(r"\b([a-zA-Z0-9][a-zA-Z0-9\-]{1,62}\.[a-zA-Z]{2,})\b", text)
                if m:
                    return m.group(1).lower()
            except Exception:
                return None
    except ImportError:
        pass
    return None


def _build_routes(db, get_current_user, get_owner_user, fernet_obj):
    """Wire up routes with closures over db + auth deps from server.py."""

    # ============= USER ROUTES =============

    @router.post("/verify/submit")
    async def submit_verification(
        background_tasks: BackgroundTasks,
        company_name: str = Form(...),
        company_domain: str = Form(...),
        submitted_email: str = Form(...),
        device_fingerprint: str = Form("{}"),
        ip_ranges: str = Form(""),
        auth_letter: UploadFile = File(...),
        id_card: UploadFile = File(...),
        selfie: UploadFile = File(...),
        user=Depends(get_current_user),
    ):
        # Reject if already approved & not expired
        existing = await db.enterprise_verification.find_one(
            {"user_id": user.id, "status": "approved"}, {"_id": 0}
        )
        if existing:
            exp = existing.get("expires_at")
            if exp and datetime.fromisoformat(exp) > datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="You already have active enterprise verification")

        try:
            fp = json.loads(device_fingerprint or "{}")
        except json.JSONDecodeError:
            fp = {"raw": device_fingerprint[:500]}

        auth_path, _ = await _save_upload(auth_letter, "letter")
        id_path, _ = await _save_upload(id_card, "id")
        selfie_path, _ = await _save_upload(selfie, "selfie")

        token = secrets.token_urlsafe(24)
        rec = {
            "id": str(uuid.uuid4()),
            "user_id": user.id,
            "user_email": user.email,
            "company_name": company_name.strip(),
            "company_domain": company_domain.strip().lower(),
            "auth_letter_path": auth_path,
            "id_card_path": id_path,
            "selfie_path": selfie_path,
            "device_fingerprint": fp,
            "submitted_email": submitted_email.strip().lower(),
            "ip_ranges": [r.strip() for r in ip_ranges.split(",") if r.strip()],
            "company_email_verified": False,
            "company_verification_token": token,
            "status": "pending_docs",
            "reviewed_by": None,
            "approved_at": None,
            "expires_at": None,
            "notes": "",
            "face_match_score": None,
            "face_match_simulated": True,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.enterprise_verification.insert_one(rec)

        background_tasks.add_task(_run_verification_pipeline, db, rec["id"])

        public_link = f"/api/enterprise/verify/company-approve?token={token}"
        return {
            "id": rec["id"],
            "status": rec["status"],
            "message": "Verification submitted. Owner will review after company-email confirmation.",
            "company_verification_link": public_link,
            "company_verification_email_target": f"security@{rec['company_domain']}",
        }

    @router.get("/verify/status")
    async def get_my_verification(user=Depends(get_current_user)):
        rec = await db.enterprise_verification.find_one(
            {"user_id": user.id},
            {"_id": 0, "auth_letter_path": 0, "id_card_path": 0, "selfie_path": 0},
            sort=[("submitted_at", -1)],
        )
        if not rec:
            return {"has_verification": False, "has_network_scan_permission": False}
        # Check expiry
        active = False
        if rec.get("status") == "approved" and rec.get("expires_at"):
            active = datetime.fromisoformat(rec["expires_at"]) > datetime.now(timezone.utc)
        return {
            "has_verification": True,
            "has_network_scan_permission": active,
            "verification": rec,
        }

    @router.get("/verify/company-approve")
    async def company_email_approve(token: str):
        rec = await db.enterprise_verification.find_one({"company_verification_token": token}, {"_id": 0})
        if not rec:
            raise HTTPException(status_code=404, detail="Invalid or expired token")
        if rec["status"] in ("approved", "rejected", "expired"):
            return {"ok": True, "status": rec["status"], "message": "Already finalized"}
        await db.enterprise_verification.update_one(
            {"id": rec["id"]},
            {"$set": {
                "company_email_verified": True,
                "status": "pending_owner",
                "company_verified_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return {
            "ok": True,
            "status": "pending_owner",
            "message": "Company email confirmed. Owner approval pending.",
            "company_name": rec["company_name"],
        }

    # ============= NETWORK SCANNER =============

    async def _has_network_permission(user) -> bool:
        if user.role == "owner":
            return True
        rec = await db.enterprise_verification.find_one(
            {"user_id": user.id, "status": "approved"}, {"_id": 0}
        )
        if not rec:
            return False
        exp = rec.get("expires_at")
        return bool(exp and datetime.fromisoformat(exp) > datetime.now(timezone.utc))

    @router.post("/start-scan")
    async def start_scan(
        body: StartScanRequest,
        background_tasks: BackgroundTasks,
        user=Depends(get_current_user),
    ):
        if not await _has_network_permission(user):
            raise HTTPException(status_code=403, detail="Network scanner requires approved enterprise verification")

        # Basic rate-limit: max 1 active scan per user
        active = await db.network_scans.find_one(
            {"user_id": user.id, "status": {"$in": ["queued", "running"]}}, {"_id": 0}
        )
        if active:
            raise HTTPException(status_code=429, detail="An active scan is already running")

        scan_id = str(uuid.uuid4())
        doc = {
            "id": scan_id,
            "user_id": user.id,
            "ip_ranges": body.ip_ranges,
            "ports": body.ports or "22,445,3389,5985,5986",
            "protocols": body.protocols or ["tcp"],
            "credentials_used": body.credentials_used,
            "status": "queued",
            "progress": "queued",
            "graph": {"nodes": [], "edges": [], "weak_endpoints": [], "summary": {}},
            "hosts_total": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        await db.network_scans.insert_one(doc)

        background_tasks.add_task(_run_network_scan, db, scan_id, body.ip_ranges, doc["ports"])
        return {"id": scan_id, "status": "queued"}

    @router.get("/network-scans")
    async def list_my_network_scans(user=Depends(get_current_user)):
        if not await _has_network_permission(user):
            raise HTTPException(status_code=403, detail="Network scanner not enabled")
        rows = await db.network_scans.find(
            {"user_id": user.id},
            {"_id": 0, "graph": 0},
        ).sort("started_at", -1).to_list(50)
        return {"scans": rows}

    @router.get("/network-scans/{scan_id}")
    async def get_network_scan(scan_id: str, user=Depends(get_current_user)):
        if not await _has_network_permission(user):
            raise HTTPException(status_code=403, detail="Network scanner not enabled")
        doc = await db.network_scans.find_one({"id": scan_id, "user_id": user.id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Scan not found")
        return doc

    @router.get("/network-scans/{scan_id}/export")
    async def export_network_scan(scan_id: str, format: str = "json", user=Depends(get_current_user)):
        if not await _has_network_permission(user):
            raise HTTPException(status_code=403, detail="Network scanner not enabled")
        doc = await db.network_scans.find_one({"id": scan_id, "user_id": user.id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Scan not found")

        if format == "json":
            return JSONResponse(doc)

        if format == "pdf":
            try:
                from fpdf import FPDF
            except ImportError:
                raise HTTPException(status_code=500, detail="PDF generation not available")
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 18)
            pdf.cell(0, 10, "Network Defense Scan Report", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, f"Scan ID: {scan_id}", ln=True)
            pdf.cell(0, 6, f"Targets: {', '.join(doc.get('ip_ranges', []))[:200]}", ln=True)
            pdf.cell(0, 6, f"Started: {doc.get('started_at', '')}", ln=True)
            pdf.cell(0, 6, f"Status: {doc.get('status', '')}", ln=True)
            pdf.ln(4)
            summary = doc.get("graph", {}).get("summary", {})
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Summary", ln=True)
            pdf.set_font("Helvetica", "", 10)
            for k, v in summary.items():
                pdf.cell(0, 6, f"  {k.replace('_', ' ').title()}: {v}", ln=True)
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Weak Endpoints", ln=True)
            pdf.set_font("Helvetica", "", 9)
            for w in doc.get("graph", {}).get("weak_endpoints", [])[:50]:
                line = f"[{w.get('level', '').upper()}] {w.get('ip')} - {w.get('label')} (port {w.get('port')})"
                pdf.multi_cell(0, 5, line)
                pdf.set_text_color(120, 120, 120)
                pdf.multi_cell(0, 5, f"    Remediation: {w.get('remediation', '')}")
                pdf.set_text_color(0, 0, 0)
                pdf.ln(1)

            pdf_bytes = bytes(pdf.output(dest="S"))
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="network_scan_{scan_id[:8]}.pdf"'},
            )

        raise HTTPException(status_code=400, detail="format must be json or pdf")

    # ============= OWNER ROUTES =============

    @owner_router.get("")
    async def list_pending(user=Depends(get_owner_user)):
        rows = await db.enterprise_verification.find(
            {}, {"_id": 0, "device_fingerprint": 0},
        ).sort("submitted_at", -1).to_list(200)
        return {"verifications": rows}

    @owner_router.get("/{verif_id}")
    async def get_verification(verif_id: str, user=Depends(get_owner_user)):
        rec = await db.enterprise_verification.find_one({"id": verif_id}, {"_id": 0})
        if not rec:
            raise HTTPException(status_code=404, detail="Not found")
        return rec

    @owner_router.get("/{verif_id}/file/{kind}")
    async def serve_verification_file(verif_id: str, kind: str, user=Depends(get_owner_user)):
        if kind not in ("auth_letter", "id_card", "selfie"):
            raise HTTPException(status_code=400, detail="Invalid kind")
        rec = await db.enterprise_verification.find_one({"id": verif_id}, {"_id": 0})
        if not rec:
            raise HTTPException(status_code=404, detail="Not found")
        path = rec.get(f"{kind}_path")
        if not path or not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File missing")
        return FileResponse(path)

    @owner_router.post("/{verif_id}/approve")
    async def approve_verification(verif_id: str, body: VerificationDecision, user=Depends(get_owner_user)):
        rec = await db.enterprise_verification.find_one({"id": verif_id}, {"_id": 0})
        if not rec:
            raise HTTPException(status_code=404, detail="Not found")
        now = datetime.now(timezone.utc)
        await db.enterprise_verification.update_one(
            {"id": verif_id},
            {"$set": {
                "status": "approved",
                "reviewed_by": user.id,
                "approved_at": now.isoformat(),
                "expires_at": (now + timedelta(days=30)).isoformat(),
                "notes": body.notes or "",
            }},
        )
        await db.users.update_one(
            {"id": rec["user_id"]}, {"$set": {"has_network_scan_permission": True}}
        )
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action_type": "enterprise_verification_approved",
            "performed_by": user.id, "target_user": rec["user_id"],
            "details": f"Approved verification for {rec['company_name']}",
            "timestamp": now.isoformat(),
        })
        return {
            "ok": True,
            "expires_at": (now + timedelta(days=30)).isoformat(),
            "auto_email_sent": False,
            "user_email": rec["user_email"],
            "message": "Approved. SMTP not configured - notify the user manually or via the in-app notification.",
        }

    @owner_router.post("/{verif_id}/reject")
    async def reject_verification(verif_id: str, body: VerificationDecision, user=Depends(get_owner_user)):
        rec = await db.enterprise_verification.find_one({"id": verif_id}, {"_id": 0})
        if not rec:
            raise HTTPException(status_code=404, detail="Not found")
        now = datetime.now(timezone.utc)
        await db.enterprise_verification.update_one(
            {"id": verif_id},
            {"$set": {
                "status": "rejected", "reviewed_by": user.id,
                "approved_at": None, "expires_at": None,
                "notes": body.notes or "Rejected",
                "rejected_at": now.isoformat(),
            }},
        )
        await db.users.update_one(
            {"id": rec["user_id"]}, {"$set": {"has_network_scan_permission": False}}
        )
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action_type": "enterprise_verification_rejected",
            "performed_by": user.id, "target_user": rec["user_id"],
            "details": body.notes or "Rejected",
            "timestamp": now.isoformat(),
        })
        return {"ok": True}

    @owner_router.post("/{verif_id}/revoke")
    async def revoke_verification(verif_id: str, user=Depends(get_owner_user)):
        rec = await db.enterprise_verification.find_one({"id": verif_id}, {"_id": 0})
        if not rec:
            raise HTTPException(status_code=404, detail="Not found")
        now = datetime.now(timezone.utc)
        await db.enterprise_verification.update_one(
            {"id": verif_id},
            {"$set": {"status": "expired", "expires_at": now.isoformat(), "revoked_by": user.id}},
        )
        await db.users.update_one(
            {"id": rec["user_id"]}, {"$set": {"has_network_scan_permission": False}}
        )
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action_type": "enterprise_verification_revoked",
            "performed_by": user.id, "target_user": rec["user_id"],
            "details": "Revoked", "timestamp": now.isoformat(),
        })
        return {"ok": True}

    return router, owner_router


# ---------- BACKGROUND TASKS ----------

async def _run_verification_pipeline(db, verif_id: str):
    """Validate auth letter, simulate face check, advance status."""
    try:
        rec = await db.enterprise_verification.find_one({"id": verif_id}, {"_id": 0})
        if not rec:
            return
        domain_in_letter = _extract_company_from_letter(rec.get("auth_letter_path", ""))
        # Simulated face match (hook for real API)
        face_score = 0.92 if rec.get("selfie_path") and rec.get("id_card_path") else 0.0

        update = {
            "letter_domain_extracted": domain_in_letter,
            "letter_domain_match": (domain_in_letter == rec.get("company_domain")) if domain_in_letter else None,
            "face_match_score": face_score,
            "face_match_passed": face_score >= 0.75,
            "docs_processed_at": datetime.now(timezone.utc).isoformat(),
        }
        # Advance to pending_company (waiting for company-email click)
        if rec["status"] == "pending_docs":
            update["status"] = "pending_company"
        await db.enterprise_verification.update_one({"id": verif_id}, {"$set": update})
    except Exception as e:
        logger.exception("verification pipeline failed: %s", e)


async def _run_network_scan(db, scan_id: str, ip_ranges: list[str], ports: str):
    """Background task: run real nmap + service checks, store graph."""
    from services.network_scanner import run_full_scan

    async def progress(stage, msg):
        await db.network_scans.update_one(
            {"id": scan_id}, {"$set": {"status": "running", "progress": f"{stage}: {msg}"}}
        )

    try:
        await db.network_scans.update_one(
            {"id": scan_id}, {"$set": {"status": "running", "progress": "starting"}}
        )
        result = await run_full_scan(ip_ranges, ports=ports, progress_cb=progress)
        graph = result.get("graph", {"nodes": [], "edges": [], "weak_endpoints": [], "summary": {}})
        await db.network_scans.update_one(
            {"id": scan_id},
            {"$set": {
                "status": "completed",
                "progress": "completed",
                "graph": graph,
                "hosts_total": len(result.get("hosts", {})),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "raw_targets": result.get("targets", []),
            }},
        )
    except Exception as e:
        logger.exception("network scan failed")
        await db.network_scans.update_one(
            {"id": scan_id},
            {"$set": {"status": "failed", "progress": f"error: {e}",
                       "completed_at": datetime.now(timezone.utc).isoformat()}},
        )
