"""Main scanner orchestrator - combines API results with local heuristics"""
import hashlib
import os
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from services.scanners.apis import (
    vt_scan_url, vt_scan_file, urlscan_scan, urlhaus_check,
    urlhaus_check_hash, malwarebazaar_check, extract_vt_stats
)
from services.scanners.pe_scanner import scan_pe_file
from services.scanners.pdf_scanner import scan_pdf_file
from services.scanners.zip_scanner import scan_zip_file
from services.scanners.doc_scanner import scan_doc_file
from services.scanners.apk_scanner import scan_apk_file
from services.scanners.image_scanner import scan_image_file

logger = logging.getLogger(__name__)

# Sensitivity thresholds
SENSITIVITY = {
    "low": {"min_confidence": 90, "score_multiplier": 0.6},
    "normal": {"min_confidence": 50, "score_multiplier": 1.0},
    "high": {"min_confidence": 25, "score_multiplier": 1.3},
    "aggressive": {"min_confidence": 10, "score_multiplier": 1.6}
}

# File type detection
FILE_SIGNATURES = {
    b'\x4d\x5a': 'exe',  # MZ header
    b'\x7f\x45\x4c\x46': 'elf',
    b'\x50\x4b\x03\x04': 'zip',
    b'\x25\x50\x44\x46': 'pdf',
    b'\xd0\xcf\x11\xe0': 'ole',  # DOC, XLS, PPT
    b'\xff\xd8\xff': 'jpg',
    b'\x89\x50\x4e\x47': 'png',
    b'\x47\x49\x46\x38': 'gif',
    b'\x42\x4d': 'bmp',
    b'\x52\x61\x72\x21': 'rar',
}

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.ico'}
DOC_EXTENSIONS = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.rtf'}
ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z', '.tar', '.gz', '.jar'}


def detect_file_type(file_bytes: bytes, filename: str) -> str:
    """Detect real file type from magic bytes and extension"""
    ext = os.path.splitext(filename)[1].lower() if '.' in filename else ''

    # Check magic bytes
    for sig, ftype in FILE_SIGNATURES.items():
        if file_bytes[:len(sig)] == sig:
            if ftype == 'zip' and ext == '.apk':
                return 'apk'
            if ftype == 'zip' and ext in DOC_EXTENSIONS:
                return 'doc'
            if ftype == 'ole':
                return 'doc'
            return ftype

    # Fallback to extension
    if ext in ('.exe', '.dll', '.sys', '.scr'):
        return 'exe'
    if ext == '.pdf':
        return 'pdf'
    if ext in DOC_EXTENSIONS:
        return 'doc'
    if ext in ARCHIVE_EXTENSIONS:
        return 'zip'
    if ext == '.apk':
        return 'apk'
    if ext in IMAGE_EXTENSIONS:
        return 'image'

    return 'unknown'


async def check_cache(db, cache_key: str) -> Optional[dict]:
    """Check if we have a cached result less than 24h old"""
    cached = await db.scan_cache.find_one({"cache_key": cache_key}, {"_id": 0})
    if cached:
        cached_time = datetime.fromisoformat(cached["cached_at"])
        if datetime.now(timezone.utc) - cached_time < timedelta(hours=24):
            return cached.get("result")
    return None


async def store_cache(db, cache_key: str, result: dict):
    """Cache a scan result"""
    await db.scan_cache.update_one(
        {"cache_key": cache_key},
        {"$set": {"cache_key": cache_key, "result": result, "cached_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )


async def scan_url_full(url: str, sensitivity: str, db, user_plan: str) -> dict:
    """Full URL scan with all engines and scoring"""
    cache_key = f"url:{hashlib.sha256(url.encode()).hexdigest()}"
    cached = await check_cache(db, cache_key)
    if cached:
        cached["from_cache"] = True
        return cached

    sens = SENSITIVITY.get(sensitivity, SENSITIVITY["normal"])
    api_results = []

    # Always call URLhaus (free, no key)
    urlhaus_result = await urlhaus_check(url)
    api_results.append(urlhaus_result)

    # Call VirusTotal
    vt_result = await vt_scan_url(url)
    api_results.append(vt_result)

    # Call urlscan.io for premium+
    if user_plan in ("premium", "enterprise"):
        urlscan_result = await urlscan_scan(url)
        api_results.append(urlscan_result)

    # Compute score using the formula:
    # risk_score = (VT_positives / VT_total * 100) * 0.6 + (urlscan_malicious ? 30 : 0) + (URLhaus_detected ? 20 : 0)
    vt_stats = extract_vt_stats(vt_result)
    vt_score = (vt_stats["positives"] / max(vt_stats["total"], 1)) * 100

    urlhaus_score = 0
    urlhaus_data = urlhaus_result.get("data", {})
    if urlhaus_data.get("query_status") == "ok" or urlhaus_data.get("url_status") in ("online", "offline"):
        if urlhaus_data.get("url_status") == "online" or urlhaus_data.get("threat"):
            urlhaus_score = 20

    urlscan_score = 0
    for r in api_results:
        if r.get("source") == "urlscan" and not r.get("error"):
            verdicts = r.get("data", {}).get("verdicts", {})
            if verdicts.get("overall", {}).get("malicious") or verdicts.get("urlscan", {}).get("malicious"):
                urlscan_score = 30

    raw_score = vt_score * 0.6 + urlscan_score + urlhaus_score
    final_score = min(int(raw_score * sens["score_multiplier"]), 100)

    # Determine risk level
    if final_score >= 70:
        risk_level = "critical"
    elif final_score >= 40:
        risk_level = "high"
    elif final_score >= 15:
        risk_level = "suspicious"
    elif final_score > 0:
        risk_level = "low"
    else:
        risk_level = "safe"

    # Build explanations
    explanations = []
    if vt_stats["positives"] > 0:
        explanations.append(f"VirusTotal: {vt_stats['positives']}/{vt_stats['total']} engines detected as malicious")
    if urlhaus_score > 0:
        explanations.append(f"URLhaus: URL listed as {urlhaus_data.get('threat', 'malicious')}")
    if urlscan_score > 0:
        explanations.append("urlscan.io: Flagged as malicious")
    if not explanations:
        if vt_result.get("error"):
            explanations.append(f"VirusTotal: {vt_result['error']}")
        explanations.append("No threats detected by any scanner")

    # Extract IOCs
    iocs = extract_url_iocs(url, api_results)

    result = {
        "risk_score": final_score,
        "risk_level": risk_level,
        "sensitivity": sensitivity,
        "explanations": explanations,
        "detections": vt_stats["detections"],
        "engines_detected": vt_stats["positives"],
        "engines_total": vt_stats["total"],
        "urlhaus_detected": urlhaus_score > 0,
        "urlscan_malicious": urlscan_score > 0,
        "iocs": iocs,
        "api_results_raw": api_results,
        "from_cache": False
    }

    await store_cache(db, cache_key, {k: v for k, v in result.items() if k != "api_results_raw"})
    return result


async def scan_file_full(file_bytes: bytes, filename: str, sensitivity: str, db, user_plan: str) -> dict:
    """Full file scan with type detection, heuristics, and API queries"""
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    cache_key = f"file:{file_hash}"
    cached = await check_cache(db, cache_key)
    if cached:
        cached["from_cache"] = True
        return cached

    sens = SENSITIVITY.get(sensitivity, SENSITIVITY["normal"])
    file_type = detect_file_type(file_bytes, filename)
    api_results = []

    # 1. External API scans
    vt_result = await vt_scan_file(file_bytes, filename)
    api_results.append(vt_result)

    mb_result = await malwarebazaar_check(file_hash)
    api_results.append(mb_result)

    uh_result = await urlhaus_check_hash(file_hash)
    api_results.append(uh_result)

    # 2. Local heuristic scan based on file type
    heuristic_result = {"heuristic_score": 0, "findings": [], "scan_type": "generic"}
    if file_type == 'exe':
        heuristic_result = scan_pe_file(file_bytes)
    elif file_type == 'pdf':
        heuristic_result = scan_pdf_file(file_bytes)
    elif file_type == 'zip':
        heuristic_result = scan_zip_file(file_bytes)
    elif file_type == 'doc':
        heuristic_result = scan_doc_file(file_bytes, filename)
    elif file_type == 'apk':
        heuristic_result = scan_apk_file(file_bytes)
    elif file_type == 'image':
        heuristic_result = scan_image_file(file_bytes, filename)

    # 3. Compute combined score
    # VT score (0-100) * 0.5 + heuristic_score (0-100) * 0.3 + external_db_score * 0.2
    vt_stats = extract_vt_stats(vt_result)
    vt_score = (vt_stats["positives"] / max(vt_stats["total"], 1)) * 100

    heuristic_score = heuristic_result.get("heuristic_score", 0)

    # External DB score (MalwareBazaar + URLhaus hash)
    ext_score = 0
    mb_data = mb_result.get("data", {})
    if mb_data.get("query_status") == "ok":
        ext_score += 50
    uh_data = uh_result.get("data", {})
    if uh_data.get("query_status") == "ok":
        ext_score += 50
    ext_score = min(ext_score, 100)

    raw_score = vt_score * 0.5 + heuristic_score * 0.3 + ext_score * 0.2
    final_score = min(int(raw_score * sens["score_multiplier"]), 100)

    # Risk level
    if final_score >= 70:
        risk_level = "critical"
    elif final_score >= 40:
        risk_level = "high"
    elif final_score >= 15:
        risk_level = "suspicious"
    elif final_score > 0:
        risk_level = "low"
    else:
        risk_level = "safe"

    # Explanations
    explanations = []
    if vt_stats["positives"] > 0:
        explanations.append(f"VirusTotal: {vt_stats['positives']}/{vt_stats['total']} detections")
    if mb_data.get("query_status") == "ok":
        mb_info = mb_data.get("data", [{}])
        if isinstance(mb_info, list) and mb_info:
            explanations.append(f"MalwareBazaar: Known malware ({mb_info[0].get('signature', 'detected')})")
    if uh_data.get("query_status") == "ok":
        explanations.append("URLhaus: Hash found in malware database")

    for finding in heuristic_result.get("findings", [])[:10]:
        if finding.get("score", 0) >= sens["min_confidence"] * 0.5:
            explanations.append(f"[{file_type.upper()}] {finding['detail']}")

    if not explanations:
        if vt_result.get("error"):
            explanations.append(f"VirusTotal: {vt_result['error']}")
        explanations.append("No threats detected")

    # IOCs
    iocs = extract_file_iocs(file_hash, filename, file_type, api_results, heuristic_result)

    result = {
        "risk_score": final_score,
        "risk_level": risk_level,
        "sensitivity": sensitivity,
        "file_type_detected": file_type,
        "file_hash": file_hash,
        "file_size": len(file_bytes),
        "explanations": explanations,
        "detections": vt_stats["detections"],
        "engines_detected": vt_stats["positives"],
        "engines_total": vt_stats["total"],
        "heuristic_result": {k: v for k, v in heuristic_result.items() if k != "raw_results"},
        "iocs": iocs,
        "api_results_raw": api_results,
        "from_cache": False
    }

    await store_cache(db, cache_key, {k: v for k, v in result.items() if k != "api_results_raw"})
    return result


def extract_url_iocs(url: str, api_results: list) -> list:
    """Extract IOCs from URL scan results"""
    iocs = []
    iocs.append({"ioc_type": "url", "value": url, "confidence": 100})
    domain_match = re.search(r'https?://([^/:]+)', url)
    if domain_match:
        iocs.append({"ioc_type": "domain", "value": domain_match.group(1), "confidence": 95})

    for result in api_results:
        if result.get("error"):
            continue
        data = result.get("data", {})
        source = result.get("source", "")

        if source == "urlscan":
            page = data.get("page", {})
            if page.get("ip"):
                iocs.append({"ioc_type": "ip", "value": page["ip"], "confidence": 80})
            lists_data = data.get("lists", {})
            for ip in (lists_data.get("ips") or [])[:10]:
                iocs.append({"ioc_type": "ip", "value": ip, "confidence": 60})
            for domain in (lists_data.get("domains") or [])[:10]:
                iocs.append({"ioc_type": "domain", "value": domain, "confidence": 60})

        elif source == "urlhaus":
            if data.get("threat"):
                iocs.append({"ioc_type": "malware_family", "value": data["threat"], "confidence": 85})
            for payload in (data.get("payloads") or [])[:5]:
                if payload.get("sha256_hash"):
                    iocs.append({"ioc_type": "sha256", "value": payload["sha256_hash"], "confidence": 90})

    # Deduplicate
    seen = set()
    unique = []
    for ioc in iocs:
        key = f"{ioc['ioc_type']}:{ioc['value']}"
        if key not in seen:
            seen.add(key)
            unique.append(ioc)
    return unique


def extract_file_iocs(file_hash: str, filename: str, file_type: str, api_results: list, heuristic: dict) -> list:
    """Extract IOCs from file scan results"""
    iocs = [
        {"ioc_type": "sha256", "value": file_hash, "confidence": 100},
        {"ioc_type": "filename", "value": filename, "confidence": 100}
    ]

    # From file_info (PE scanner)
    file_info = heuristic.get("file_info", {})
    if file_info.get("md5"):
        iocs.append({"ioc_type": "md5", "value": file_info["md5"], "confidence": 100})

    # From API results
    for result in api_results:
        if result.get("error"):
            continue
        data = result.get("data", {})
        source = result.get("source", "")

        if source == "malwarebazaar" and data.get("query_status") == "ok":
            mb_data = data.get("data", [])
            if isinstance(mb_data, list):
                for entry in mb_data[:3]:
                    if entry.get("signature"):
                        iocs.append({"ioc_type": "malware_family", "value": entry["signature"], "confidence": 90})
                    if entry.get("md5_hash"):
                        iocs.append({"ioc_type": "md5", "value": entry["md5_hash"], "confidence": 100})

    # From heuristic (suspicious imports, permissions, etc.)
    if file_type == "exe":
        for imp in heuristic.get("imports_suspicious", [])[:5]:
            iocs.append({"ioc_type": "suspicious_api", "value": imp["function"], "confidence": imp.get("risk_score", 50)})
    elif file_type == "apk":
        for lib in heuristic.get("suspicious_libraries", [])[:5]:
            iocs.append({"ioc_type": "suspicious_library", "value": lib["library"], "confidence": lib.get("score", 50)})

    # Deduplicate
    seen = set()
    unique = []
    for ioc in iocs:
        key = f"{ioc['ioc_type']}:{ioc['value']}"
        if key not in seen:
            seen.add(key)
            unique.append(ioc)
    return unique
