"""Backend tests for new scanner orchestrator with sensitivity parameter."""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://linkshield-demo.preview.emergentagent.com').rstrip('/')
OWNER_EMAIL = "athulkrishna456727@gmail.com"
OWNER_PASSWORD = "#AThr401012#"


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}


# ---------- URL Scan Tests ----------

class TestScanURL:
    def test_scan_url_low_sensitivity(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                          json={"url": "https://example.com/test-low", "sensitivity": "low"}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("id", "risk_score", "risk_level", "sensitivity", "explanations",
                  "engines_detected", "engines_total", "iocs"):
            assert k in data, f"Missing field: {k}"
        assert data["sensitivity"] == "low"
        assert isinstance(data["explanations"], list)

    def test_scan_url_aggressive_sensitivity(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                          json={"url": "https://example.com/test-agg", "sensitivity": "aggressive"}, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["sensitivity"] == "aggressive"

    def test_scan_url_invalid_sensitivity_falls_back(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                          json={"url": "https://example.com/test-foo", "sensitivity": "foobar"}, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["sensitivity"] == "normal"

    def test_scan_url_default_sensitivity(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                          json={"url": "https://example.com/test-def"}, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["sensitivity"] == "normal"

    def test_graceful_missing_vt_key(self, owner_headers):
        """VT_API_KEY not configured - should not 500 and explanations include VT note"""
        r = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                          json={"url": "https://example.com/vt-fallback", "sensitivity": "normal"}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        # With no VT key, engines_detected should be 0
        assert data["engines_detected"] == 0
        assert isinstance(data["explanations"], list)

    def test_cache_hit_same_url(self, owner_headers):
        url = f"https://example.com/cache-{int(time.time())}"
        r1 = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                           json={"url": url, "sensitivity": "normal"}, timeout=60)
        assert r1.status_code == 200
        assert r1.json().get("from_cache") is False
        r2 = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                           json={"url": url, "sensitivity": "normal"}, timeout=60)
        assert r2.status_code == 200
        assert r2.json().get("from_cache") is True

    def test_get_scan_by_id(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                          json={"url": "https://example.com/getscan", "sensitivity": "high"}, timeout=60)
        assert r.status_code == 200
        scan_id = r.json()["id"]
        g = requests.get(f"{BASE_URL}/api/scan/{scan_id}", headers=owner_headers, timeout=15)
        assert g.status_code == 200, g.text
        gd = g.json()
        assert gd["id"] == scan_id
        assert gd["sensitivity"] == "high"
        assert "explanations" in gd
        assert "engines_detected" in gd

    def test_iocs_endpoint(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                          json={"url": "https://example.com/iocs-test"}, timeout=60)
        scan_id = r.json()["id"]
        ir = requests.get(f"{BASE_URL}/api/iocs/scan/{scan_id}", headers=owner_headers, timeout=15)
        assert ir.status_code == 200
        d = ir.json()
        assert "iocs" in d and isinstance(d["iocs"], list)
        assert d["scan_id"] == scan_id


# ---------- File Scan Tests ----------

class TestScanFile:
    def test_scan_file_pdf_high(self, owner_token):
        headers = {"Authorization": f"Bearer {owner_token}"}
        pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
        files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        r = requests.post(f"{BASE_URL}/api/scan/file?sensitivity=high",
                          headers=headers, files=files, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["file_type_detected"] == "pdf"
        assert data["sensitivity"] == "high"
        assert "heuristic_score" in data
        assert "explanations" in data

    def test_scan_file_exe_normal(self, owner_token):
        headers = {"Authorization": f"Bearer {owner_token}"}
        # MZ header + padding
        exe_bytes = b"MZ" + b"\x00" * 200
        files = {"file": ("test.exe", io.BytesIO(exe_bytes), "application/octet-stream")}
        r = requests.post(f"{BASE_URL}/api/scan/file?sensitivity=normal",
                          headers=headers, files=files, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["file_type_detected"] == "exe"
        assert data["sensitivity"] == "normal"


# ---------- Regression tests ----------

class TestAuthRegression:
    def test_owner_login_and_me(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == OWNER_EMAIL

    def test_billing_plans_public(self):
        r = requests.get(f"{BASE_URL}/api/billing/plans", timeout=10)
        assert r.status_code == 200
        plans = r.json()
        assert len(plans) == 3
