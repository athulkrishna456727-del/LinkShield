"""PDF scanner - detect JavaScript, exploits, embedded files"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Suspicious PDF keywords
EXPLOIT_INDICATORS = {
    "/OpenAction": 15, "/AA": 12, "/JavaScript": 20, "/JS": 20,
    "/Launch": 25, "/EmbeddedFile": 15, "/RichMedia": 10,
    "/AcroForm": 5, "/XFA": 10, "/URI": 3,
    "/SubmitForm": 10, "/GoToR": 8, "/GoToE": 8
}

# Known exploit patterns
EXPLOIT_PATTERNS = [
    (r"util\.printf", "CVE-2008-2992 (util.printf overflow)", 30),
    (r"Collab\.collectEmailInfo", "CVE-2007-5659 (collectEmailInfo)", 30),
    (r"Collab\.getIcon", "CVE-2009-0927 (getIcon overflow)", 30),
    (r"spell\.customDictionaryOpen", "CVE-2009-1493 (customDictionaryOpen)", 30),
    (r"media\.newPlayer", "CVE-2009-4324 (media.newPlayer)", 30),
    (r"getAnnots", "CVE-2009-1492 (getAnnots)", 25),
    (r"app\.doc", "Potential document manipulation", 10),
    (r"this\.exportDataObject", "Data exfiltration attempt", 20),
    (r"eval\s*\(", "JavaScript eval() - code execution", 20),
    (r"unescape\s*\(", "Obfuscated payload (unescape)", 15),
    (r"String\.fromCharCode", "Character-based obfuscation", 12),
    (r"\\x[0-9a-fA-F]{2}", "Hex-encoded strings (possible shellcode)", 10),
    (r"%u[0-9a-fA-F]{4}", "Unicode-encoded payload (heap spray)", 25),
]

# Deobfuscation patterns
OBFUSCATION_PATTERNS = [
    (r"var\s+\w+\s*=\s*['\"][\w\+\-\*\/\%]+['\"]", "String concatenation obfuscation", 10),
    (r"replace\s*\(\s*/[^/]+/", "Regex-based deobfuscation", 8),
    (r"(?:concat|join|split)\s*\(", "Array manipulation obfuscation", 8),
    (r"setTimeout|setInterval", "Delayed execution", 5),
]


def scan_pdf_file(file_bytes: bytes) -> dict:
    """Scan PDF for malicious content using static analysis"""
    result = {
        "scan_type": "pdf_analysis",
        "heuristic_score": 0,
        "findings": [],
        "javascript_present": False,
        "embedded_files": False,
        "exploit_indicators": [],
        "suspicious_objects": [],
        "page_count": 0
    }

    content = file_bytes.decode('latin-1', errors='ignore')

    # Basic PDF validation
    if not content.startswith('%PDF'):
        result["findings"].append({"type": "invalid_pdf", "detail": "File does not start with %PDF header", "score": 5})

    # Count pages
    page_count = content.count('/Type /Page') - content.count('/Type /Pages')
    result["page_count"] = max(page_count, content.count('/Page'))

    # Check for exploit indicators
    for keyword, score in EXPLOIT_INDICATORS.items():
        count = content.count(keyword)
        if count > 0:
            result["exploit_indicators"].append(keyword)
            if keyword in ("/JavaScript", "/JS"):
                result["javascript_present"] = True
                result["findings"].append({
                    "type": "javascript_found",
                    "detail": f"JavaScript detected ({keyword} found {count}x)",
                    "score": score
                })
            elif keyword == "/EmbeddedFile":
                result["embedded_files"] = True
                result["findings"].append({
                    "type": "embedded_file",
                    "detail": f"Embedded file detected ({count}x)",
                    "score": score
                })
            elif keyword in ("/OpenAction", "/AA", "/Launch"):
                result["findings"].append({
                    "type": "auto_action",
                    "detail": f"Auto-execution trigger: {keyword} ({count}x)",
                    "score": score
                })
            else:
                result["findings"].append({
                    "type": "suspicious_keyword",
                    "detail": f"Suspicious keyword: {keyword} ({count}x)",
                    "score": score
                })
            result["heuristic_score"] += score

    # Extract JavaScript blocks and check for exploits
    js_blocks = re.findall(r'(?:stream\s*\n)(.*?)(?:\nendstream)', content, re.DOTALL)
    all_js_content = " ".join(js_blocks)

    for pattern, description, score in EXPLOIT_PATTERNS:
        matches = re.findall(pattern, all_js_content, re.IGNORECASE)
        if matches:
            result["findings"].append({
                "type": "exploit_pattern",
                "detail": f"{description} (matched {len(matches)}x)",
                "score": score
            })
            result["heuristic_score"] += score

    # Check for obfuscation
    for pattern, description, score in OBFUSCATION_PATTERNS:
        matches = re.findall(pattern, all_js_content, re.IGNORECASE)
        if matches:
            result["findings"].append({
                "type": "obfuscation",
                "detail": f"{description} (matched {len(matches)}x)",
                "score": score
            })
            result["heuristic_score"] += score

    # Check for streams with high entropy (possible shellcode)
    stream_count = content.count('stream')
    if stream_count > 50:
        result["findings"].append({
            "type": "many_streams",
            "detail": f"Unusually many streams ({stream_count}) - possible payload hiding",
            "score": 10
        })
        result["heuristic_score"] += 10

    # Check for suspicious object types
    obj_patterns = [
        (r'/Type\s*/Action', "Action objects"),
        (r'/S\s*/JavaScript', "JavaScript action"),
        (r'/Type\s*/Filespec', "File specification"),
    ]
    for pattern, desc in obj_patterns:
        matches = re.findall(pattern, content)
        if matches:
            result["suspicious_objects"].append({"type": desc, "count": len(matches)})

    # Cap at 100
    result["heuristic_score"] = min(result["heuristic_score"], 100)
    return result
