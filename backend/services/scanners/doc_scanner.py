"""DOC/DOCX scanner - macro detection and exploit analysis using oletools"""
import logging
import io
import re
import zipfile

logger = logging.getLogger(__name__)

# Suspicious VBA patterns
SUSPICIOUS_VBA = {
    "AutoOpen": 20, "Auto_Open": 20, "Document_Open": 20, "Workbook_Open": 20,
    "AutoExec": 20, "AutoClose": 15, "Document_Close": 15,
    "Shell": 15, "WScript.Shell": 20, "Powershell": 25,
    "CreateObject": 12, "GetObject": 10,
    "CallByName": 15, "Environ": 10,
    "URLDownloadToFile": 25, "XMLHTTP": 15,
    "ADODB.Stream": 15, "Scripting.FileSystemObject": 12,
    "cmd.exe": 25, "cmd /c": 25,
    "base64": 15, "Chr(": 10, "ChrW(": 10,
    "StrReverse": 12, "Replace(": 5,
    "Kill ": 10, "FileCopy": 8,
    "RegWrite": 15, "RegRead": 10,
    "Sleep": 5, "Wait": 5,
}

# Known CVEs
CVE_PATTERNS = [
    (r"Equation\.3|MathType", "CVE-2017-11882 (Equation Editor RCE)", 40),
    (r"Package|OLE2Link", "CVE-2017-0199 (OLE2Link exploit)", 35),
    (r"DDE|DDEAUTO", "DDE Command Execution", 30),
    (r"\\objupdate|\\objautlink", "RTF Object Auto-Update", 25),
]


def scan_doc_file(file_bytes: bytes, filename: str) -> dict:
    """Scan DOC/DOCX for malicious macros and exploits"""
    result = {
        "scan_type": "document_analysis",
        "heuristic_score": 0,
        "findings": [],
        "has_macros": False,
        "macro_count": 0,
        "auto_exec_macros": [],
        "suspicious_strings": [],
        "obfuscation_detected": False
    }

    ext = filename.lower().split('.')[-1] if '.' in filename else ''

    # Try oletools for OLE files
    try:
        from oletools.olevba import VBA_Parser
        vba_parser = VBA_Parser(filename, data=file_bytes)

        if vba_parser.detect_vba_macros():
            result["has_macros"] = True
            result["findings"].append({
                "type": "macros_present",
                "detail": "VBA macros detected in document",
                "score": 15
            })
            result["heuristic_score"] += 15

            macro_code = ""
            macro_count = 0
            for (_, _, vba_filename, vba_code) in vba_parser.extract_macros():
                macro_count += 1
                macro_code += vba_code + "\n"

            result["macro_count"] = macro_count

            # Check for suspicious patterns
            for pattern, score in SUSPICIOUS_VBA.items():
                if pattern.lower() in macro_code.lower():
                    result["suspicious_strings"].append(pattern)
                    is_auto_exec = pattern in ("AutoOpen", "Auto_Open", "Document_Open", "Workbook_Open", "AutoExec")
                    if is_auto_exec:
                        result["auto_exec_macros"].append(pattern)
                        result["findings"].append({
                            "type": "auto_exec_macro",
                            "detail": f"Auto-execute macro: {pattern}",
                            "score": score
                        })
                    else:
                        result["findings"].append({
                            "type": "suspicious_vba",
                            "detail": f"Suspicious VBA pattern: {pattern}",
                            "score": score
                        })
                    result["heuristic_score"] += score

            # Obfuscation detection
            chr_count = macro_code.lower().count("chr(") + macro_code.lower().count("chrw(")
            concat_count = macro_code.count("&") + macro_code.count("+")
            if chr_count > 10 or (concat_count > 50 and chr_count > 5):
                result["obfuscation_detected"] = True
                result["findings"].append({
                    "type": "obfuscation",
                    "detail": f"Heavy obfuscation detected (Chr calls: {chr_count}, concatenations: {concat_count})",
                    "score": 20
                })
                result["heuristic_score"] += 20

        vba_parser.close()
    except Exception as e:
        logger.warning(f"oletools parse failed: {e}")
        # Fallback: raw binary analysis
        content = file_bytes.decode('latin-1', errors='ignore')
        if 'vbaProject' in content or 'VBA' in content or 'Macros' in content:
            result["has_macros"] = True
            result["findings"].append({
                "type": "macros_present",
                "detail": "VBA macros detected (binary pattern match)",
                "score": 15
            })
            result["heuristic_score"] += 15

    # Check for CVE patterns (works for DOC and RTF)
    content_str = file_bytes.decode('latin-1', errors='ignore')
    for pattern, description, score in CVE_PATTERNS:
        if re.search(pattern, content_str, re.IGNORECASE):
            result["findings"].append({
                "type": "cve_pattern",
                "detail": description,
                "score": score
            })
            result["heuristic_score"] += score

    # Check DOCX (ZIP-based) for suspicious content
    if ext in ('docx', 'xlsx', 'pptx'):
        try:
            zf = zipfile.ZipFile(io.BytesIO(file_bytes))
            names = zf.namelist()
            # External links (potential SSRF/download)
            for name in names:
                if 'rels' in name.lower():
                    try:
                        rels_content = zf.read(name).decode('utf-8', errors='ignore')
                        if 'External' in rels_content and ('http://' in rels_content or 'https://' in rels_content):
                            result["findings"].append({
                                "type": "external_link",
                                "detail": f"External resource reference in {name}",
                                "score": 10
                            })
                            result["heuristic_score"] += 10
                    except Exception:
                        pass
            # Check for vbaProject.bin
            if 'word/vbaProject.bin' in names or 'xl/vbaProject.bin' in names:
                if not result["has_macros"]:
                    result["has_macros"] = True
                    result["heuristic_score"] += 15
            zf.close()
        except Exception:
            pass

    result["heuristic_score"] = min(result["heuristic_score"], 100)
    return result
