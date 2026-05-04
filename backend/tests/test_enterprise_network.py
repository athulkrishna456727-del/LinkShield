"""Backend tests for Enterprise Verification + Network Scanner feature."""
import io
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://linkshield-demo.preview.emergentagent.com").rstrip("/")

OWNER_EMAIL = "athulkrishna456727@gmail.com"
OWNER_PASS = "#AThr401012#"
ADMIN_EMAIL = "athulmark401012@gmail.com"
ADMIN_PASS = "dgskgsnskz"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def owner_token():
    return _login(OWNER_EMAIL, OWNER_PASS)


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------- Enterprise verification submission (as admin user, so they need verification) ----------

class TestVerificationFlow:
    state = {}

    def _fake_files(self):
        # tiny PDF (valid header)
        pdf = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
               b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
               b"trailer<</Root 1 0 R>>\n%%EOF\n")
        png_1x1 = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6300010000000500010d0a2db40000000049454e44ae426082")
        return {
            "auth_letter": ("letter.pdf", pdf, "application/pdf"),
            "id_card": ("id.png", png_1x1, "image/png"),
            "selfie": ("selfie.png", png_1x1, "image/png"),
        }

    def test_submit_verification(self, admin_headers):
        files = self._fake_files()
        data = {
            "company_name": "TEST_AcmeCorp",
            "company_domain": "acme.example.com",
            "submitted_email": "security@acme.example.com",
            "device_fingerprint": '{"visitorId":"test-visitor-123"}',
            "ip_ranges": "127.0.0.1/32",
        }
        r = requests.post(f"{BASE_URL}/api/enterprise/verify/submit",
                          headers=admin_headers, data=data, files=files)
        # Admin may already have active verification from previous run; retry GET to clean state
        if r.status_code == 400 and "already have active" in r.text:
            pytest.skip("Admin already has active verification; cannot re-submit in this run")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "pending_docs"
        assert "company_verification_link" in body
        assert "token=" in body["company_verification_link"]
        TestVerificationFlow.state["verif_id"] = body["id"]
        TestVerificationFlow.state["link"] = body["company_verification_link"]
        TestVerificationFlow.state["token"] = body["company_verification_link"].split("token=")[1]

    def test_pipeline_transitions_to_pending_company(self, admin_headers):
        if "verif_id" not in TestVerificationFlow.state:
            pytest.skip("submit skipped")
        # background task transitions pending_docs -> pending_company
        deadline = time.time() + 10
        status = None
        while time.time() < deadline:
            r = requests.get(f"{BASE_URL}/api/enterprise/verify/status", headers=admin_headers)
            assert r.status_code == 200
            status = r.json().get("verification", {}).get("status")
            if status == "pending_company":
                break
            time.sleep(1)
        assert status == "pending_company", f"expected pending_company got {status}"

    def test_company_approve_link(self, admin_headers):
        if "token" not in TestVerificationFlow.state:
            pytest.skip("submit skipped")
        r = requests.get(f"{BASE_URL}/api/enterprise/verify/company-approve",
                         params={"token": TestVerificationFlow.state["token"]})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "pending_owner"

    def test_status_shows_pending_owner(self, admin_headers):
        if "verif_id" not in TestVerificationFlow.state:
            pytest.skip("")
        r = requests.get(f"{BASE_URL}/api/enterprise/verify/status", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["has_verification"] is True
        assert body["verification"]["status"] == "pending_owner"
        assert body["verification"]["company_email_verified"] is True

    def test_owner_lists_verifications(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/owner/verification", headers=owner_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "verifications" in body
        assert isinstance(body["verifications"], list)

    def test_owner_gets_detail(self, owner_headers):
        if "verif_id" not in TestVerificationFlow.state:
            pytest.skip("")
        vid = TestVerificationFlow.state["verif_id"]
        r = requests.get(f"{BASE_URL}/api/owner/verification/{vid}", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["id"] == vid

    def test_owner_serves_files(self, owner_headers):
        if "verif_id" not in TestVerificationFlow.state:
            pytest.skip("")
        vid = TestVerificationFlow.state["verif_id"]
        for kind in ("auth_letter", "id_card", "selfie"):
            r = requests.get(f"{BASE_URL}/api/owner/verification/{vid}/file/{kind}",
                             headers=owner_headers)
            assert r.status_code == 200, f"{kind}: {r.status_code}"
            assert len(r.content) > 0

    def test_start_scan_forbidden_without_approval(self, admin_headers):
        # Admin has pending_owner status (not approved) - should get 403
        r = requests.post(f"{BASE_URL}/api/enterprise/start-scan",
                          headers=admin_headers,
                          json={"ip_ranges": ["127.0.0.1"], "ports": "22,80"})
        assert r.status_code == 403
        assert "verification" in r.text.lower()

    def test_owner_approves_verification(self, owner_headers):
        if "verif_id" not in TestVerificationFlow.state:
            pytest.skip("")
        vid = TestVerificationFlow.state["verif_id"]
        r = requests.post(f"{BASE_URL}/api/owner/verification/{vid}/approve",
                          headers=owner_headers,
                          json={"notes": "TEST_ automated approval", "auto_send_email": False})
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        assert "expires_at" in r.json()

    def test_admin_now_has_permission(self, admin_headers):
        if "verif_id" not in TestVerificationFlow.state:
            pytest.skip("")
        r = requests.get(f"{BASE_URL}/api/enterprise/verify/status", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["has_network_scan_permission"] is True
        assert body["verification"]["status"] == "approved"

    def test_owner_revokes_cleanup(self, owner_headers):
        """Cleanup: revoke to keep admin in unverified state for next run."""
        if "verif_id" not in TestVerificationFlow.state:
            pytest.skip("")
        vid = TestVerificationFlow.state["verif_id"]
        r = requests.post(f"{BASE_URL}/api/owner/verification/{vid}/revoke", headers=owner_headers)
        assert r.status_code == 200


# ---------- Network scanner as owner (bypasses verification) ----------

class TestNetworkScanner:
    state = {}

    def test_owner_start_scan(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/enterprise/start-scan",
                          headers=owner_headers,
                          json={"ip_ranges": ["127.0.0.1"], "ports": "22,80,443"})
        # If an active scan exists, allow 429
        if r.status_code == 429:
            pytest.skip("active scan already running - skip to avoid conflict")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "queued"
        assert "id" in body
        TestNetworkScanner.state["scan_id"] = body["id"]

    def test_scan_completes(self, owner_headers):
        if "scan_id" not in TestNetworkScanner.state:
            pytest.skip("")
        sid = TestNetworkScanner.state["scan_id"]
        deadline = time.time() + 60
        status = None
        doc = {}
        while time.time() < deadline:
            r = requests.get(f"{BASE_URL}/api/enterprise/network-scans/{sid}", headers=owner_headers)
            assert r.status_code == 200
            doc = r.json()
            status = doc.get("status")
            if status in ("completed", "failed"):
                break
            time.sleep(2)
        assert status == "completed", f"scan status={status}, progress={doc.get('progress')}"
        assert doc.get("hosts_total", 0) >= 1, f"hosts_total={doc.get('hosts_total')}"
        graph = doc.get("graph", {})
        assert "nodes" in graph and "edges" in graph
        assert len(graph.get("nodes", [])) >= 1

    def test_list_scans(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/enterprise/network-scans", headers=owner_headers)
        assert r.status_code == 200
        assert "scans" in r.json()

    def test_export_json(self, owner_headers):
        if "scan_id" not in TestNetworkScanner.state:
            pytest.skip("")
        sid = TestNetworkScanner.state["scan_id"]
        r = requests.get(f"{BASE_URL}/api/enterprise/network-scans/{sid}/export",
                         headers=owner_headers, params={"format": "json"})
        assert r.status_code == 200
        assert r.json()["id"] == sid

    def test_export_pdf(self, owner_headers):
        if "scan_id" not in TestNetworkScanner.state:
            pytest.skip("")
        sid = TestNetworkScanner.state["scan_id"]
        r = requests.get(f"{BASE_URL}/api/enterprise/network-scans/{sid}/export",
                         headers=owner_headers, params={"format": "pdf"})
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF")


# ---------- Regression ----------

class TestRegression:
    def test_scan_url_still_works(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/scan/url", headers=owner_headers,
                          json={"url": "https://example.com", "sensitivity": "normal"})
        assert r.status_code == 200

    def test_history_still_works(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/scans/history", headers=owner_headers)
        assert r.status_code == 200
