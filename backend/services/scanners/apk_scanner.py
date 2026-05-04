"""APK scanner - Android application analysis using androguard"""
import logging
import zipfile
import io
import re

logger = logging.getLogger(__name__)

# Dangerous Android permissions
DANGEROUS_PERMISSIONS = {
    "android.permission.SEND_SMS": 15,
    "android.permission.READ_SMS": 12,
    "android.permission.RECEIVE_SMS": 12,
    "android.permission.READ_CONTACTS": 10,
    "android.permission.WRITE_CONTACTS": 10,
    "android.permission.READ_CALL_LOG": 10,
    "android.permission.WRITE_CALL_LOG": 10,
    "android.permission.RECORD_AUDIO": 12,
    "android.permission.CAMERA": 10,
    "android.permission.ACCESS_FINE_LOCATION": 8,
    "android.permission.READ_PHONE_STATE": 8,
    "android.permission.CALL_PHONE": 12,
    "android.permission.WRITE_EXTERNAL_STORAGE": 5,
    "android.permission.READ_EXTERNAL_STORAGE": 3,
    "android.permission.INTERNET": 2,
    "android.permission.SYSTEM_ALERT_WINDOW": 12,
    "android.permission.BIND_DEVICE_ADMIN": 20,
    "android.permission.BIND_ACCESSIBILITY_SERVICE": 18,
    "android.permission.REQUEST_INSTALL_PACKAGES": 15,
    "android.permission.WRITE_SETTINGS": 10,
    "android.permission.RECEIVE_BOOT_COMPLETED": 8,
}

# Suspicious libraries/packages
SUSPICIOUS_PACKAGES = [
    ("com.koushikdutta", "Ion HTTP library (data exfiltration)", 5),
    ("org.apache.http", "Apache HTTP (network comm)", 3),
    ("javax.crypto", "Cryptography usage", 5),
    ("dalvik.system.DexClassLoader", "Dynamic code loading", 20),
    ("java.lang.reflect", "Reflection (code hiding)", 10),
    ("android.telephony.SmsManager", "SMS sending capability", 15),
    ("android.app.admin.DeviceAdminReceiver", "Device admin (ransomware pattern)", 25),
    ("android.accessibilityservice", "Accessibility service (overlay attack)", 20),
]


def scan_apk_file(file_bytes: bytes) -> dict:
    """Scan APK file for suspicious permissions and behaviors"""
    result = {
        "scan_type": "apk_analysis",
        "heuristic_score": 0,
        "findings": [],
        "permissions": [],
        "dangerous_permissions": [],
        "app_info": {},
        "suspicious_libraries": [],
        "dex_files": 0,
        "native_libs": []
    }

    try:
        from androguard.core.apk import APK
        apk = APK(file_bytes, raw=True)

        # App info
        result["app_info"] = {
            "package": apk.get_package(),
            "app_name": apk.get_app_name(),
            "version": apk.get_androidversion_name(),
            "min_sdk": apk.get_min_sdk_version(),
            "target_sdk": apk.get_target_sdk_version(),
        }

        # Permissions analysis
        permissions = apk.get_permissions()
        result["permissions"] = list(permissions)

        for perm in permissions:
            if perm in DANGEROUS_PERMISSIONS:
                score = DANGEROUS_PERMISSIONS[perm]
                result["dangerous_permissions"].append({"permission": perm, "risk_score": score})
                result["heuristic_score"] += score

        if len(result["dangerous_permissions"]) > 5:
            result["findings"].append({
                "type": "excessive_permissions",
                "detail": f"{len(result['dangerous_permissions'])} dangerous permissions requested",
                "score": 15
            })
            result["heuristic_score"] += 15

        # Activities/receivers/services check
        receivers = apk.get_receivers()
        if receivers:
            boot_receivers = [r for r in receivers if 'BOOT' in str(apk.get_intent_filters('receiver', r))]
            if boot_receivers:
                result["findings"].append({
                    "type": "boot_receiver",
                    "detail": "App starts on device boot (persistence)",
                    "score": 10
                })
                result["heuristic_score"] += 10

    except Exception as e:
        logger.warning(f"androguard parse failed: {e}, falling back to ZIP analysis")
        # Fallback: parse as ZIP
        try:
            zf = zipfile.ZipFile(io.BytesIO(file_bytes))
            names = zf.namelist()

            # Count DEX files
            dex_files = [n for n in names if n.endswith('.dex')]
            result["dex_files"] = len(dex_files)
            if len(dex_files) > 3:
                result["findings"].append({
                    "type": "multi_dex",
                    "detail": f"Multiple DEX files ({len(dex_files)}) - possible code hiding",
                    "score": 5
                })
                result["heuristic_score"] += 5

            # Check for native libraries
            native = [n for n in names if '.so' in n]
            result["native_libs"] = native[:10]
            if native:
                result["findings"].append({
                    "type": "native_code",
                    "detail": f"Native libraries detected ({len(native)} .so files)",
                    "score": 5
                })
                result["heuristic_score"] += 5

            # Parse manifest if available
            if 'AndroidManifest.xml' in names:
                try:
                    manifest_bytes = zf.read('AndroidManifest.xml')
                    manifest_str = manifest_bytes.decode('utf-8', errors='ignore')
                    # Simple permission extraction from raw XML
                    perms = re.findall(r'android:name="(android\.permission\.\w+)"', manifest_str)
                    result["permissions"] = perms
                    for perm in perms:
                        if perm in DANGEROUS_PERMISSIONS:
                            score = DANGEROUS_PERMISSIONS[perm]
                            result["dangerous_permissions"].append({"permission": perm, "risk_score": score})
                            result["heuristic_score"] += score
                except Exception:
                    pass

            zf.close()
        except Exception as zip_err:
            result["findings"].append({"type": "parse_error", "detail": f"Could not parse APK: {str(zip_err)}", "score": 0})

    # Check for suspicious libraries in DEX content
    try:
        zf = zipfile.ZipFile(io.BytesIO(file_bytes))
        for name in zf.namelist():
            if name.endswith('.dex'):
                try:
                    dex_content = zf.read(name).decode('latin-1', errors='ignore')
                    for pkg, desc, score in SUSPICIOUS_PACKAGES:
                        if pkg in dex_content:
                            result["suspicious_libraries"].append({"library": pkg, "description": desc, "score": score})
                            result["findings"].append({
                                "type": "suspicious_library",
                                "detail": f"{desc}: {pkg}",
                                "score": score
                            })
                            result["heuristic_score"] += score
                except Exception:
                    pass
        zf.close()
    except Exception:
        pass

    # Cap score
    result["heuristic_score"] = min(result["heuristic_score"], 100)
    return result
