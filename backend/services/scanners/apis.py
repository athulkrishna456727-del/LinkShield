"""External API integrations: VirusTotal, urlscan.io, URLhaus, MalwareBazaar"""
import os
import hashlib
import httpx
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Ensure .env is loaded even if this module is imported before server.py finishes init
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')


def _vt_key() -> str:
    return os.environ.get("VT_API_KEY", "")


def _urlscan_key() -> str:
    return os.environ.get("URLSCAN_API_KEY", "")


VT_BASE = "https://www.virustotal.com/api/v3"
URLSCAN_BASE = "https://urlscan.io/api/v1"
URLHAUS_BASE = "https://urlhaus-api.abuse.ch/v1"
MALWAREBAZAAR_BASE = "https://mb-api.abuse.ch/api/v1"


async def vt_scan_url(url: str) -> dict:
    """Submit URL to VirusTotal and retrieve analysis"""
    VT_API_KEY = _vt_key()
    if not VT_API_KEY:
        return {"source": "virustotal", "error": "VT_API_KEY not configured"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{VT_BASE}/urls",
                headers={"x-apikey": VT_API_KEY},
                data={"url": url}
            )
            if resp.status_code == 200:
                data = resp.json()
                analysis_id = data.get("data", {}).get("id")
                if analysis_id:
                    # Poll for result (up to 30s)
                    for _ in range(6):
                        await asyncio.sleep(5)
                        result = await client.get(
                            f"{VT_BASE}/analyses/{analysis_id}",
                            headers={"x-apikey": VT_API_KEY}
                        )
                        if result.status_code == 200:
                            rdata = result.json()
                            status = rdata.get("data", {}).get("attributes", {}).get("status")
                            if status == "completed":
                                return {"source": "virustotal", "data": rdata}
                    # Return whatever we have
                    return {"source": "virustotal", "data": rdata if result.status_code == 200 else None, "note": "analysis_pending"}
            elif resp.status_code == 429:
                return {"source": "virustotal", "error": "Rate limited (4 req/min on free tier)"}
            return {"source": "virustotal", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"source": "virustotal", "error": str(e)}


async def vt_scan_file(file_bytes: bytes, filename: str) -> dict:
    """Upload file to VirusTotal or do hash lookup"""
    VT_API_KEY = _vt_key()
    if not VT_API_KEY:
        return {"source": "virustotal", "error": "VT_API_KEY not configured"}
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # Try hash lookup first (faster, no upload needed)
            hash_resp = await client.get(
                f"{VT_BASE}/files/{file_hash}",
                headers={"x-apikey": VT_API_KEY}
            )
            if hash_resp.status_code == 200:
                return {"source": "virustotal", "data": hash_resp.json(), "method": "hash_lookup"}

            # File >32MB: hash only
            if len(file_bytes) > 32 * 1024 * 1024:
                return {"source": "virustotal", "error": "File exceeds 32MB VT limit", "hash": file_hash, "method": "hash_only"}

            # Upload file
            resp = await client.post(
                f"{VT_BASE}/files",
                headers={"x-apikey": VT_API_KEY},
                files={"file": (filename, file_bytes)}
            )
            if resp.status_code == 200:
                data = resp.json()
                analysis_id = data.get("data", {}).get("id")
                if analysis_id:
                    for _ in range(6):
                        await asyncio.sleep(10)
                        result = await client.get(
                            f"{VT_BASE}/analyses/{analysis_id}",
                            headers={"x-apikey": VT_API_KEY}
                        )
                        if result.status_code == 200:
                            rdata = result.json()
                            if rdata.get("data", {}).get("attributes", {}).get("status") == "completed":
                                return {"source": "virustotal", "data": rdata, "method": "upload"}
                    return {"source": "virustotal", "data": rdata, "method": "upload", "note": "analysis_pending"}
            elif resp.status_code == 429:
                return {"source": "virustotal", "error": "Rate limited"}
            return {"source": "virustotal", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"source": "virustotal", "error": str(e)}


async def urlscan_scan(url: str) -> dict:
    """Submit URL to urlscan.io"""
    URLSCAN_API_KEY = _urlscan_key()
    if not URLSCAN_API_KEY:
        return {"source": "urlscan", "error": "URLSCAN_API_KEY not configured"}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{URLSCAN_BASE}/scan/",
                headers={"API-Key": URLSCAN_API_KEY, "Content-Type": "application/json"},
                json={"url": url, "visibility": "unlisted"}
            )
            if resp.status_code == 200:
                data = resp.json()
                result_api = data.get("api")
                if result_api:
                    # Wait for scan to complete
                    for _ in range(4):
                        await asyncio.sleep(15)
                        result = await client.get(result_api)
                        if result.status_code == 200:
                            return {"source": "urlscan", "data": result.json()}
                    return {"source": "urlscan", "error": "Scan still processing", "uuid": data.get("uuid")}
            elif resp.status_code == 429:
                return {"source": "urlscan", "error": "Rate limited"}
            return {"source": "urlscan", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"source": "urlscan", "error": str(e)}


async def urlhaus_check(url: str) -> dict:
    """Check URL against URLhaus database (no key required)"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{URLHAUS_BASE}/url/", data={"url": url})
            if resp.status_code == 200:
                return {"source": "urlhaus", "data": resp.json()}
            return {"source": "urlhaus", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"source": "urlhaus", "error": str(e)}


async def urlhaus_check_hash(file_hash: str) -> dict:
    """Check file hash against URLhaus"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{URLHAUS_BASE}/payload/", data={"sha256_hash": file_hash})
            if resp.status_code == 200:
                return {"source": "urlhaus_hash", "data": resp.json()}
            return {"source": "urlhaus_hash", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"source": "urlhaus_hash", "error": str(e)}


async def malwarebazaar_check(file_hash: str) -> dict:
    """Check hash against MalwareBazaar (no key required)"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{MALWAREBAZAAR_BASE}/",
                data={"query": "get_info", "hash": file_hash}
            )
            if resp.status_code == 200:
                return {"source": "malwarebazaar", "data": resp.json()}
            return {"source": "malwarebazaar", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"source": "malwarebazaar", "error": str(e)}


def extract_vt_stats(vt_result: dict) -> dict:
    """Extract detection stats from VT response"""
    if not vt_result or vt_result.get("error"):
        return {"positives": 0, "total": 0, "detections": [], "permalink": ""}
    data = vt_result.get("data", {})
    attrs = data.get("data", {}).get("attributes", {})
    stats = attrs.get("stats", attrs.get("last_analysis_stats", {}))
    positives = stats.get("malicious", 0) + stats.get("suspicious", 0)
    total = sum(stats.values()) if stats else 0

    detections = []
    results_map = attrs.get("results", attrs.get("last_analysis_results", {}))
    if isinstance(results_map, dict):
        for engine, detail in results_map.items():
            if isinstance(detail, dict) and detail.get("category") in ("malicious", "suspicious"):
                detections.append({"engine": engine, "result": detail.get("result", "detected"), "category": detail["category"]})

    return {"positives": positives, "total": total, "detections": detections[:30], "permalink": ""}
