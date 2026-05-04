"""EXE/PE file static analysis using pefile"""
import pefile
import math
import hashlib
import logging
from typing import List

logger = logging.getLogger(__name__)

# Suspicious Windows API imports
SUSPICIOUS_IMPORTS = {
    "VirtualAllocEx": 15, "WriteProcessMemory": 15, "CreateRemoteThread": 15,
    "NtUnmapViewOfSection": 12, "SetWindowsHookEx": 10, "GetAsyncKeyState": 10,
    "InternetOpen": 5, "URLDownloadToFile": 10, "ShellExecute": 8,
    "WinExec": 8, "CreateProcess": 5, "OpenProcess": 8,
    "VirtualProtect": 8, "LoadLibrary": 3, "GetProcAddress": 3,
    "RegSetValueEx": 5, "RegCreateKey": 5, "CryptEncrypt": 8,
    "FindFirstFile": 3, "FindNextFile": 3, "IsDebuggerPresent": 10,
    "CheckRemoteDebuggerPresent": 10, "NtSetInformationThread": 10,
    "GetTickCount": 5, "QueryPerformanceCounter": 5,
}

# Known packer signatures
PACKER_SIGNATURES = ["UPX", "MPRESS", "ASPack", "PECompact", "Themida", "VMProtect", "Armadillo", "Obsidium"]


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


def scan_pe_file(file_bytes: bytes) -> dict:
    """Perform static analysis on PE (EXE/DLL) file"""
    result = {
        "scan_type": "pe_static",
        "heuristic_score": 0,
        "findings": [],
        "sections": [],
        "imports_suspicious": [],
        "packer_detected": None,
        "has_signature": False,
        "file_info": {}
    }

    try:
        pe = pefile.PE(data=file_bytes)
    except pefile.PEFormatError as e:
        result["findings"].append({"type": "error", "detail": f"Invalid PE format: {str(e)}", "score": 0})
        return result
    except Exception as e:
        result["findings"].append({"type": "error", "detail": f"Parse error: {str(e)}", "score": 0})
        return result

    # File info
    result["file_info"] = {
        "sha256": hashlib.sha256(file_bytes).hexdigest(),
        "md5": hashlib.md5(file_bytes).hexdigest(),
        "size": len(file_bytes),
        "is_dll": pe.is_dll(),
        "is_exe": pe.is_exe(),
        "machine": hex(pe.FILE_HEADER.Machine),
        "timestamp": pe.FILE_HEADER.TimeDateStamp
    }

    # Section analysis
    high_entropy_sections = 0
    for section in pe.sections:
        name = section.Name.decode('utf-8', errors='ignore').strip('\x00')
        entropy = calculate_entropy(section.get_data())
        section_info = {
            "name": name,
            "entropy": round(entropy, 2),
            "virtual_size": section.Misc_VirtualSize,
            "raw_size": section.SizeOfRawData
        }
        result["sections"].append(section_info)

        if entropy > 7.0:
            high_entropy_sections += 1
            result["findings"].append({
                "type": "high_entropy",
                "detail": f"Section '{name}' has entropy {entropy:.2f} (likely packed/encrypted)",
                "score": 15
            })
            result["heuristic_score"] += 15

    # Overall file entropy
    file_entropy = calculate_entropy(file_bytes)
    if file_entropy > 7.2:
        result["findings"].append({
            "type": "packed_file",
            "detail": f"Overall file entropy {file_entropy:.2f} suggests packing/encryption",
            "score": 20
        })
        result["heuristic_score"] += 20

    # Import table analysis
    if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll_name = entry.dll.decode('utf-8', errors='ignore') if entry.dll else ""
            for imp in entry.imports:
                if imp.name:
                    func_name = imp.name.decode('utf-8', errors='ignore')
                    if func_name in SUSPICIOUS_IMPORTS:
                        score = SUSPICIOUS_IMPORTS[func_name]
                        result["imports_suspicious"].append({
                            "dll": dll_name,
                            "function": func_name,
                            "risk_score": score
                        })
                        result["findings"].append({
                            "type": "suspicious_import",
                            "detail": f"Suspicious API: {func_name} from {dll_name}",
                            "score": score
                        })
                        result["heuristic_score"] += score

    # Packer detection
    for section in pe.sections:
        name = section.Name.decode('utf-8', errors='ignore').strip('\x00').upper()
        for packer in PACKER_SIGNATURES:
            if packer.upper() in name:
                result["packer_detected"] = packer
                result["findings"].append({
                    "type": "packer_detected",
                    "detail": f"Packer signature detected: {packer}",
                    "score": 20
                })
                result["heuristic_score"] += 20
                break

    # Digital signature check
    has_sig = False
    if hasattr(pe, 'DIRECTORY_ENTRY_SECURITY'):
        has_sig = True
    result["has_signature"] = has_sig
    if not has_sig:
        result["findings"].append({
            "type": "no_signature",
            "detail": "No digital signature found (unsigned binary)",
            "score": 10
        })
        result["heuristic_score"] += 10

    # Anti-debug techniques
    if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
        all_imports = []
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for imp in entry.imports:
                if imp.name:
                    all_imports.append(imp.name.decode('utf-8', errors='ignore'))
        anti_debug = [i for i in all_imports if i in ("IsDebuggerPresent", "CheckRemoteDebuggerPresent", "NtSetInformationThread", "OutputDebugString")]
        if len(anti_debug) >= 2:
            result["findings"].append({
                "type": "anti_debug",
                "detail": f"Multiple anti-debugging techniques: {', '.join(anti_debug)}",
                "score": 15
            })
            result["heuristic_score"] += 15

    # Cap at 100
    result["heuristic_score"] = min(result["heuristic_score"], 100)
    pe.close()
    return result
