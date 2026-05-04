"""ZIP/Archive scanner - recursive extraction and zip bomb detection"""
import zipfile
import io
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

MAX_DEPTH = 10
MAX_FILES = 5000
MAX_DECOMPRESSED_SIZE = 1 * 1024 * 1024 * 1024  # 1GB
BOMB_RATIO_THRESHOLD = 1000


def detect_zip_bomb(file_bytes: bytes) -> dict:
    """Detect zip bomb characteristics"""
    result = {"is_bomb": False, "ratio": 0, "reason": ""}
    compressed_size = len(file_bytes)

    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes))
        total_uncompressed = sum(info.file_size for info in zf.infolist())
        if compressed_size > 0:
            ratio = total_uncompressed / compressed_size
            result["ratio"] = round(ratio, 1)
            if ratio > BOMB_RATIO_THRESHOLD:
                result["is_bomb"] = True
                result["reason"] = f"Compression ratio {ratio:.0f}:1 exceeds threshold ({BOMB_RATIO_THRESHOLD}:1)"
            elif total_uncompressed > MAX_DECOMPRESSED_SIZE:
                result["is_bomb"] = True
                result["reason"] = f"Decompressed size {total_uncompressed / (1024*1024*1024):.1f}GB exceeds 1GB limit"
        zf.close()
    except Exception as e:
        result["error"] = str(e)
    return result


def extract_and_catalog(file_bytes: bytes, max_depth: int = MAX_DEPTH) -> dict:
    """Extract ZIP recursively and catalog contents"""
    result = {
        "files": [],
        "total_files": 0,
        "nested_archives": 0,
        "file_types": {},
        "suspicious_extensions": [],
        "errors": []
    }

    SUSPICIOUS_EXTENSIONS = {'.exe', '.dll', '.bat', '.cmd', '.vbs', '.js', '.ps1', '.scr', '.pif', '.com', '.hta', '.wsf'}

    def _extract(data: bytes, depth: int, prefix: str):
        if depth > max_depth:
            result["errors"].append(f"Max recursion depth ({max_depth}) reached at {prefix}")
            return
        if result["total_files"] > MAX_FILES:
            result["errors"].append(f"Max file count ({MAX_FILES}) exceeded")
            return

        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except (zipfile.BadZipFile, Exception) as e:
            result["errors"].append(f"Cannot open archive at {prefix}: {str(e)}")
            return

        for info in zf.infolist():
            if info.is_dir():
                continue
            if result["total_files"] > MAX_FILES:
                break

            full_path = f"{prefix}/{info.filename}" if prefix else info.filename
            ext = os.path.splitext(info.filename)[1].lower()
            result["total_files"] += 1

            file_entry = {
                "path": full_path,
                "size": info.file_size,
                "compressed_size": info.compress_size,
                "extension": ext
            }
            result["files"].append(file_entry)

            # Track file types
            result["file_types"][ext] = result["file_types"].get(ext, 0) + 1

            # Check suspicious extensions
            if ext in SUSPICIOUS_EXTENSIONS:
                result["suspicious_extensions"].append(full_path)

            # Recurse into nested archives
            if ext in ('.zip', '.jar', '.apk', '.docx', '.xlsx', '.pptx'):
                try:
                    nested_data = zf.read(info.filename)
                    result["nested_archives"] += 1
                    _extract(nested_data, depth + 1, full_path)
                except Exception:
                    pass

        zf.close()

    _extract(file_bytes, 0, "")
    return result


def scan_zip_file(file_bytes: bytes) -> dict:
    """Full ZIP archive analysis"""
    result = {
        "scan_type": "archive_analysis",
        "heuristic_score": 0,
        "findings": [],
        "bomb_detection": None,
        "contents": None,
        "individual_scores": []
    }

    # Zip bomb detection
    bomb = detect_zip_bomb(file_bytes)
    result["bomb_detection"] = bomb
    if bomb["is_bomb"]:
        result["findings"].append({
            "type": "zip_bomb",
            "detail": f"ZIP BOMB detected: {bomb['reason']}",
            "score": 30
        })
        result["heuristic_score"] += 30
        return result  # Don't extract bombs

    # Extract and catalog
    catalog = extract_and_catalog(file_bytes)
    result["contents"] = {
        "total_files": catalog["total_files"],
        "nested_archives": catalog["nested_archives"],
        "file_types": catalog["file_types"],
        "errors": catalog["errors"][:5]
    }

    # Score based on suspicious content
    sus_exts = catalog["suspicious_extensions"]
    if sus_exts:
        score = min(len(sus_exts) * 10, 40)
        result["findings"].append({
            "type": "suspicious_files",
            "detail": f"{len(sus_exts)} suspicious executable(s) found: {', '.join(sus_exts[:5])}",
            "score": score
        })
        result["heuristic_score"] += score

    # Check for double extensions (e.g., report.pdf.exe)
    double_ext_files = [f for f in catalog["files"] if len(os.path.splitext(os.path.splitext(f["path"])[0])[1]) > 0 and os.path.splitext(f["path"])[1].lower() in ('.exe', '.scr', '.bat', '.cmd')]
    if double_ext_files:
        result["findings"].append({
            "type": "double_extension",
            "detail": f"Double-extension trick detected: {double_ext_files[0]['path']}",
            "score": 25
        })
        result["heuristic_score"] += 25

    # High compression ratio (not bomb but suspicious)
    if bomb["ratio"] > 100:
        result["findings"].append({
            "type": "high_compression",
            "detail": f"High compression ratio ({bomb['ratio']}:1)",
            "score": 10
        })
        result["heuristic_score"] += 10

    # Password protected
    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes))
        for info in zf.infolist():
            if info.flag_bits & 0x1:
                result["findings"].append({
                    "type": "password_protected",
                    "detail": "Archive contains password-protected entries",
                    "score": 10
                })
                result["heuristic_score"] += 10
                break
        zf.close()
    except Exception:
        pass

    result["heuristic_score"] = min(result["heuristic_score"], 100)
    return result
