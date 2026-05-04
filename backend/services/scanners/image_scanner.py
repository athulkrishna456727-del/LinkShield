"""Image scanner - steganography detection, metadata analysis, exploit patterns"""
import struct
import re
import math
import logging

logger = logging.getLogger(__name__)

# Suspicious EXIF software tags
SUSPICIOUS_SOFTWARE = [
    "steghide", "openstego", "snow", "jphide", "outguess",
    "invisible secrets", "coagula", "silent eye", "stegosuite"
]

# Image exploit CVEs
IMAGE_EXPLOITS = [
    (b"\xff\xd8\xff\xe0" + b"\x00" * 50 + b"\x00\x00\x00\x00" * 100, "Possible JPEG buffer overflow payload", 25),
]


def calculate_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for byte in data:
        freq[byte] += 1
    length = len(data)
    entropy = 0.0
    for f in freq:
        if f > 0:
            p = f / length
            entropy -= p * math.log2(p)
    return entropy


def detect_lsb_steganography(file_bytes: bytes) -> dict:
    """Detect LSB steganography using chi-square analysis"""
    result = {"detected": False, "confidence": 0, "method": "chi_square"}

    # Only analyze for JPEG/PNG raw pixel data
    # Simple heuristic: check if the LSB distribution is uniform (natural) or biased (stego)
    if len(file_bytes) < 1000:
        return result

    # Sample a portion of the file (skip headers)
    sample_start = min(100, len(file_bytes) // 10)
    sample = file_bytes[sample_start:sample_start + min(50000, len(file_bytes) - sample_start)]

    if not sample:
        return result

    # Count LSB values (0 and 1)
    lsb_zeros = sum(1 for b in sample if b & 1 == 0)
    lsb_ones = len(sample) - lsb_zeros
    total = len(sample)

    # In natural images, LSB distribution should be roughly 50/50
    # Steganography often makes it MORE uniform or introduces patterns
    expected = total / 2
    if expected > 0:
        chi_sq = ((lsb_zeros - expected) ** 2 / expected) + ((lsb_ones - expected) ** 2 / expected)
        # Very low chi-square can indicate stego (too perfect)
        if chi_sq < 0.5 and total > 10000:
            result["detected"] = True
            result["confidence"] = min(int((1 - chi_sq) * 50), 50)

    # Check for sequential LSB patterns (embedding signature)
    lsb_bytes = bytes([b & 1 for b in sample[:256]])
    # Look for ASCII patterns in LSB
    potential_text = ""
    for i in range(0, len(lsb_bytes) - 8, 8):
        byte_val = 0
        for j in range(8):
            byte_val = (byte_val << 1) | lsb_bytes[i + j]
        if 32 <= byte_val <= 126:
            potential_text += chr(byte_val)

    if len(potential_text) > 5 and any(c.isalpha() for c in potential_text):
        result["detected"] = True
        result["confidence"] = max(result["confidence"], 40)
        result["method"] = "lsb_text_pattern"

    return result


def check_embedded_payload(file_bytes: bytes) -> dict:
    """Check for hidden payloads appended after image data"""
    result = {"found": False, "payload_type": None, "offset": 0}

    # JPEG: data should end with FFD9
    if file_bytes[:2] == b'\xff\xd8':
        end_marker = file_bytes.rfind(b'\xff\xd9')
        if end_marker > 0 and end_marker < len(file_bytes) - 10:
            trailing = file_bytes[end_marker + 2:]
            if len(trailing) > 50:
                result["found"] = True
                result["offset"] = end_marker + 2
                result["trailing_size"] = len(trailing)
                # Check what's appended
                if trailing[:2] == b'PK':
                    result["payload_type"] = "ZIP archive"
                elif trailing[:4] == b'\x7fELF':
                    result["payload_type"] = "ELF executable"
                elif trailing[:2] == b'MZ':
                    result["payload_type"] = "PE executable"
                elif trailing[:3] == b'Rar':
                    result["payload_type"] = "RAR archive"
                else:
                    result["payload_type"] = "unknown_data"

    # PNG: data should end with IEND chunk
    elif file_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        iend_pos = file_bytes.find(b'IEND')
        if iend_pos > 0:
            # IEND chunk is 12 bytes (4 len + 4 type + 4 crc)
            end_of_png = iend_pos + 8  # after IEND + CRC
            if end_of_png < len(file_bytes) - 20:
                trailing = file_bytes[end_of_png:]
                if len(trailing) > 50:
                    result["found"] = True
                    result["offset"] = end_of_png
                    result["trailing_size"] = len(trailing)
                    if trailing[:2] == b'PK':
                        result["payload_type"] = "ZIP archive"
                    elif trailing[:2] == b'MZ':
                        result["payload_type"] = "PE executable"
                    else:
                        result["payload_type"] = "unknown_data"

    return result


def analyze_exif(file_bytes: bytes) -> dict:
    """Analyze EXIF metadata for suspicious content"""
    result = {"suspicious": False, "findings": [], "metadata": {}}

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        import io

        img = Image.open(io.BytesIO(file_bytes))
        exif_data = img._getexif() if hasattr(img, '_getexif') and img._getexif() else {}

        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if isinstance(value, (str, bytes)):
                val_str = value.decode('utf-8', errors='ignore') if isinstance(value, bytes) else value
                result["metadata"][tag_name] = val_str[:200]

                # Check for suspicious software
                if tag_name.lower() in ('software', 'artist', 'imagedescription', 'usercomment'):
                    for sus in SUSPICIOUS_SOFTWARE:
                        if sus.lower() in val_str.lower():
                            result["suspicious"] = True
                            result["findings"].append(f"Steganography tool detected in EXIF: {sus}")

                # Check for embedded scripts
                if '<script' in val_str.lower() or 'javascript:' in val_str.lower():
                    result["suspicious"] = True
                    result["findings"].append(f"JavaScript found in EXIF field: {tag_name}")

                # Very long metadata fields (possible payload hiding)
                if len(val_str) > 1000:
                    result["suspicious"] = True
                    result["findings"].append(f"Unusually large EXIF field ({tag_name}): {len(val_str)} bytes")

        img.close()
    except Exception as e:
        # Try raw binary EXIF parsing
        content = file_bytes.decode('latin-1', errors='ignore')
        for sus in SUSPICIOUS_SOFTWARE:
            if sus.lower() in content.lower():
                result["suspicious"] = True
                result["findings"].append(f"Steganography tool signature in binary: {sus}")

    return result


def scan_image_file(file_bytes: bytes, filename: str) -> dict:
    """Full image file analysis"""
    result = {
        "scan_type": "image_analysis",
        "heuristic_score": 0,
        "findings": [],
        "steganography": None,
        "embedded_payload": None,
        "exif_analysis": None,
        "file_info": {"size": len(file_bytes), "filename": filename}
    }

    # Detect image type
    if file_bytes[:2] == b'\xff\xd8':
        result["file_info"]["format"] = "JPEG"
    elif file_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        result["file_info"]["format"] = "PNG"
    elif file_bytes[:6] in (b'GIF87a', b'GIF89a'):
        result["file_info"]["format"] = "GIF"
    elif file_bytes[:2] == b'BM':
        result["file_info"]["format"] = "BMP"
    else:
        result["file_info"]["format"] = "unknown"

    # 1. Steganography detection
    stego = detect_lsb_steganography(file_bytes)
    result["steganography"] = stego
    if stego["detected"]:
        result["findings"].append({
            "type": "steganography",
            "detail": f"LSB steganography detected (confidence: {stego['confidence']}%, method: {stego['method']})",
            "score": stego["confidence"]
        })
        result["heuristic_score"] += stego["confidence"]

    # 2. Embedded payload detection
    payload = check_embedded_payload(file_bytes)
    result["embedded_payload"] = payload
    if payload["found"]:
        score = 35 if payload["payload_type"] in ("PE executable", "ELF executable") else 20
        result["findings"].append({
            "type": "embedded_payload",
            "detail": f"Hidden payload after image data: {payload['payload_type']} ({payload.get('trailing_size', 0)} bytes at offset {payload['offset']})",
            "score": score
        })
        result["heuristic_score"] += score

    # 3. EXIF analysis
    exif = analyze_exif(file_bytes)
    result["exif_analysis"] = {"suspicious": exif["suspicious"], "findings": exif["findings"]}
    if exif["suspicious"]:
        score = len(exif["findings"]) * 15
        for finding in exif["findings"]:
            result["findings"].append({
                "type": "exif_anomaly",
                "detail": finding,
                "score": 15
            })
        result["heuristic_score"] += min(score, 30)

    # 4. Check for polyglot files (image + something else)
    content = file_bytes.decode('latin-1', errors='ignore')
    if '<?php' in content or '<script' in content:
        result["findings"].append({
            "type": "polyglot",
            "detail": "File contains executable code (PHP/JavaScript polyglot)",
            "score": 30
        })
        result["heuristic_score"] += 30

    # 5. Entropy analysis (high entropy in non-compressed formats like BMP)
    if result["file_info"]["format"] == "BMP":
        entropy = calculate_entropy(file_bytes)
        if entropy > 7.5:
            result["findings"].append({
                "type": "high_entropy_bmp",
                "detail": f"Unusual entropy for BMP ({entropy:.2f}) - possible encrypted payload",
                "score": 20
            })
            result["heuristic_score"] += 20

    result["heuristic_score"] = min(result["heuristic_score"], 100)
    return result
