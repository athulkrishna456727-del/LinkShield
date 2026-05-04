"""Real scanning service using VirusTotal, urlscan.io, URLhaus, MalwareBazaar"""
import os
import hashlib
import httpx
import asyncio
import re
from datetime import datetime, timezone
from typing import Optional

VT_API_KEY = os.environ.get("VT_API_KEY", "")
URLSCAN_API_KEY = os.environ.get("URLSCAN_API_KEY", "")
VT_BASE = "https://www.virustotal.com/api/v3"
URLSCAN_BASE = "https://urlscan.io/api/v1"
URLHAUS_BASE = "https://urlhaus-api.abuse.ch/v1"
MALWAREBAZAAR_BASE = "https://mb-api.abuse.ch/api/v1"


async def scan_url_virustotal(url: str) -> dict:
    if not VT_API_KEY:
        return {"error": "VT_API_KEY not configured", "source": "virustotal"}
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
                await asyncio.sleep(5)
                result = await client.get(
                    f"{VT_BASE}/analyses/{analysis_id}",
                    headers={"x-apikey": VT_API_KEY}
                )
                if result.status_code == 200:
                    return {"source": "virustotal", "data": result.json()}
        return {"source": "virustotal", "error": f"Status {resp.status_code}", "detail": resp.text[:200]}


async def scan_url_urlscan(url: str) -> dict:
    if not URLSCAN_API_KEY:
        return {"error": "URLSCAN_API_KEY not configured", "source": "urlscan"}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{URLSCAN_BASE}/scan/",
            headers={"API-Key": URLSCAN_API_KEY, "Content-Type": "application/json"},
            json={"url": url, "visibility": "unlisted"}
        )
        if resp.status_code == 200:
            data = resp.json()
            result_url = data.get("api")
            if result_url:
                await asyncio.sleep(15)
                result = await client.get(result_url)
                if result.status_code == 200:
                    return {"source": "urlscan", "data": result.json()}
        return {"source": "urlscan", "error": f"Status {resp.status_code}", "detail": resp.text[:200]}


async def scan_url_urlhaus(url: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{URLHAUS_BASE}/url/",
            data={"url": url}
        )
        if resp.status_code == 200:
            return {"source": "urlhaus", "data": resp.json()}
        return {"source": "urlhaus", "error": f"Status {resp.status_code}"}


async def scan_file_virustotal(file_bytes: bytes, filename: str) -> dict:
    if not VT_API_KEY:
        return {"error": "VT_API_KEY not configured", "source": "virustotal"}
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    async with httpx.AsyncClient(timeout=60) as client:
        # First check if hash already known
        hash_resp = await client.get(
            f"{VT_BASE}/files/{file_hash}",
            headers={"x-apikey": VT_API_KEY}
        )
        if hash_resp.status_code == 200:
            return {"source": "virustotal", "data": hash_resp.json(), "method": "hash_lookup"}

        # If file > 32MB, hash only
        if len(file_bytes) > 32 * 1024 * 1024:
            return {
                "source": "virustotal",
                "error": "File exceeds 32MB limit - hash lookup only",
                "hash": file_hash,
                "method": "hash_only"
            }

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
                await asyncio.sleep(10)
                result = await client.get(
                    f"{VT_BASE}/analyses/{analysis_id}",
                    headers={"x-apikey": VT_API_KEY}
                )
                if result.status_code == 200:
                    return {"source": "virustotal", "data": result.json(), "method": "upload"}
        return {"source": "virustotal", "error": f"Status {resp.status_code}"}


async def scan_file_malwarebazaar(file_hash: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{MALWAREBAZAAR_BASE}/",
            data={"query": "get_info", "hash": file_hash}
        )
        if resp.status_code == 200:
            return {"source": "malwarebazaar", "data": resp.json()}
        return {"source": "malwarebazaar", "error": f"Status {resp.status_code}"}


def compute_risk_score(results: list) -> dict:
    """Compute aggregate risk score from multiple scanner results"""
    malicious_count = 0
    suspicious_count = 0
    total_engines = 0
    threats = []

    for result in results:
        if result.get("error"):
            continue
        data = result.get("data", {})
        source = result.get("source", "")

        if source == "virustotal":
            attrs = data.get("data", {}).get("attributes", {})
            stats = attrs.get("stats", attrs.get("last_analysis_stats", {}))
            malicious_count += stats.get("malicious", 0)
            suspicious_count += stats.get("suspicious", 0)
            total_engines += sum(stats.values()) if stats else 0
            # Extract threat names
            scan_results = attrs.get("results", attrs.get("last_analysis_results", {}))
            if isinstance(scan_results, dict):
                for engine, detail in scan_results.items():
                    if isinstance(detail, dict) and detail.get("category") == "malicious":
                        threats.append({"engine": engine, "result": detail.get("result", "malicious")})

        elif source == "urlhaus":
            url_status = data.get("url_status")
            if url_status == "online":
                malicious_count += 1
                total_engines += 1
                threats.append({"engine": "URLhaus", "result": f"Listed as {data.get('threat', 'malware')}"})
            elif url_status == "offline":
                total_engines += 1
            else:
                total_engines += 1

        elif source == "malwarebazaar":
            query_status = data.get("query_status")
            if query_status == "ok":
                malicious_count += 1
                total_engines += 1
                mb_data = data.get("data", [{}])
                if isinstance(mb_data, list) and mb_data:
                    threats.append({"engine": "MalwareBazaar", "result": mb_data[0].get("signature", "known malware")})

    if total_engines == 0:
        score = 0
        level = "unknown"
    else:
        ratio = (malicious_count + suspicious_count * 0.5) / total_engines
        score = min(int(ratio * 100), 100)
        if score >= 70:
            level = "critical"
        elif score >= 40:
            level = "high"
        elif score >= 15:
            level = "suspicious"
        else:
            level = "safe"

    return {
        "risk_score": score,
        "risk_level": level,
        "malicious_detections": malicious_count,
        "suspicious_detections": suspicious_count,
        "total_engines": total_engines,
        "threats": threats[:20]
    }


def extract_iocs_from_results(results: list, target: str, scan_type: str) -> list:
    """Extract IOCs (Indicators of Compromise) from scan results"""
    iocs = []

    # Always add the scanned target as IOC
    if scan_type == "url":
        iocs.append({"ioc_type": "url", "value": target, "confidence": 100})
        # Extract domain
        domain_match = re.search(r'https?://([^/]+)', target)
        if domain_match:
            iocs.append({"ioc_type": "domain", "value": domain_match.group(1), "confidence": 90})
    elif scan_type == "file":
        iocs.append({"ioc_type": "filename", "value": target, "confidence": 100})

    for result in results:
        if result.get("error"):
            continue
        data = result.get("data", {})
        source = result.get("source", "")

        if source == "virustotal":
            attrs = data.get("data", {}).get("attributes", {})
            # File hashes
            if attrs.get("sha256"):
                iocs.append({"ioc_type": "sha256", "value": attrs["sha256"], "confidence": 100})
            if attrs.get("md5"):
                iocs.append({"ioc_type": "md5", "value": attrs["md5"], "confidence": 100})
            if attrs.get("sha1"):
                iocs.append({"ioc_type": "sha1", "value": attrs["sha1"], "confidence": 100})
            # Contacted IPs/domains from file analysis
            contacted = attrs.get("contacted_ips", [])
            for ip in contacted[:10]:
                iocs.append({"ioc_type": "ip", "value": ip, "confidence": 70})
            contacted_domains = attrs.get("contacted_domains", [])
            for d in contacted_domains[:10]:
                iocs.append({"ioc_type": "domain", "value": d, "confidence": 70})

        elif source == "urlscan":
            page = data.get("page", {})
            if page.get("ip"):
                iocs.append({"ioc_type": "ip", "value": page["ip"], "confidence": 80})
            lists_data = data.get("lists", {})
            for ip in lists_data.get("ips", [])[:10]:
                iocs.append({"ioc_type": "ip", "value": ip, "confidence": 60})
            for domain in lists_data.get("domains", [])[:10]:
                iocs.append({"ioc_type": "domain", "value": domain, "confidence": 60})

        elif source == "urlhaus":
            if data.get("threat"):
                iocs.append({"ioc_type": "malware_family", "value": data["threat"], "confidence": 85})

    # Deduplicate
    seen = set()
    unique_iocs = []
    for ioc in iocs:
        key = f"{ioc['ioc_type']}:{ioc['value']}"
        if key not in seen:
            seen.add(key)
            unique_iocs.append(ioc)
    return unique_iocs
