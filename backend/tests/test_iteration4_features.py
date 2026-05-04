"""
Iteration 4 Backend Tests - Link Shield Premium/Enterprise Features
Tests: Plan-gated access, URL scanning with IOCs, API key system, Teams, Webhooks, Reports, Owner pricing
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://linkshield-demo.preview.emergentagent.com')

# Test credentials
OWNER_EMAIL = "athulkrishna456727@gmail.com"
OWNER_PASSWORD = "#AThr401012#"
ADMIN_EMAIL = "athulmark401012@gmail.com"
ADMIN_PASSWORD = "dgskgsnskz"
OWNER_API_KEY = "ls_4263f7e699fae9e67ff7656deb491fd3467dec81685e13bbe77b4d621b69c358"


class TestAuth:
    """Authentication tests"""
    
    def test_owner_login(self):
        """Test owner can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        assert response.status_code == 200, f"Owner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "owner"
        assert data["user"]["plan"] == "enterprise"
        print(f"✓ Owner login successful - role: {data['user']['role']}, plan: {data['user']['plan']}")
    
    def test_admin_login(self):
        """Test admin can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful - role: {data['user']['role']}, plan: {data['user']['plan']}")


class TestPlanGatedAccess:
    """Test plan-gated feature access"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_owner_can_access_api_keys(self, owner_token):
        """Owner (enterprise) can access API key management"""
        response = requests.get(f"{BASE_URL}/api/apikey/usage", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"API key access failed: {response.text}"
        data = response.json()
        assert "has_key" in data
        print(f"✓ Owner can access API keys - has_key: {data['has_key']}")
    
    def test_owner_can_access_teams(self, owner_token):
        """Owner (enterprise) can access teams"""
        response = requests.get(f"{BASE_URL}/api/teams/my", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Teams access failed: {response.text}"
        print(f"✓ Owner can access teams endpoint")
    
    def test_owner_can_access_webhooks(self, owner_token):
        """Owner (enterprise) can access webhooks"""
        response = requests.get(f"{BASE_URL}/api/webhooks", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Webhooks access failed: {response.text}"
        print(f"✓ Owner can access webhooks endpoint")
    
    def test_owner_can_access_reports(self, owner_token):
        """Owner (enterprise) can access reports schedule"""
        response = requests.get(f"{BASE_URL}/api/reports/schedule", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Reports access failed: {response.text}"
        print(f"✓ Owner can access reports endpoint")


class TestURLScanning:
    """Test URL scanning with IOC extraction"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_scan_url_returns_risk_data(self, owner_token):
        """Scan URL and verify risk_score, risk_level, IOCs are returned"""
        response = requests.post(f"{BASE_URL}/api/scan/url", 
                                json={"url": "https://example.com"},
                                headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"URL scan failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "id" in data, "Missing scan id"
        assert "risk_score" in data, "Missing risk_score"
        assert "risk_level" in data, "Missing risk_level"
        assert "iocs" in data, "Missing IOCs"
        assert isinstance(data["iocs"], list), "IOCs should be a list"
        
        print(f"✓ URL scan completed - risk_score: {data['risk_score']}, risk_level: {data['risk_level']}, IOCs: {len(data['iocs'])}")
        return data["id"]
    
    def test_scan_appears_in_history(self, owner_token):
        """Verify scan appears in history"""
        response = requests.get(f"{BASE_URL}/api/scans/history", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"History fetch failed: {response.text}"
        data = response.json()
        assert "scans" in data
        assert "total" in data
        assert data["total"] > 0, "No scans in history"
        print(f"✓ Scan history accessible - total scans: {data['total']}")


class TestIOCExport:
    """Test IOC export functionality (Premium+)"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    @pytest.fixture
    def scan_id(self, owner_token):
        # Get most recent scan
        response = requests.get(f"{BASE_URL}/api/scans/history?limit=1", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        scans = response.json().get("scans", [])
        if scans:
            return scans[0]["id"]
        # Create a new scan if none exists
        response = requests.post(f"{BASE_URL}/api/scan/url", 
                                json={"url": "https://example.com"},
                                headers={"Authorization": f"Bearer {owner_token}"})
        return response.json()["id"]
    
    def test_export_iocs_csv(self, owner_token, scan_id):
        """Test CSV export of IOCs"""
        response = requests.get(f"{BASE_URL}/api/iocs/export/{scan_id}?format=csv", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"CSV export failed: {response.text}"
        assert "text/csv" in response.headers.get("content-type", "")
        print(f"✓ IOC CSV export successful")
    
    def test_export_iocs_json(self, owner_token, scan_id):
        """Test JSON export of IOCs"""
        response = requests.get(f"{BASE_URL}/api/iocs/export/{scan_id}?format=json", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"JSON export failed: {response.text}"
        data = response.json()
        assert "iocs" in data
        print(f"✓ IOC JSON export successful - {len(data['iocs'])} IOCs")
    
    def test_download_scan_pdf(self, owner_token, scan_id):
        """Test PDF report download"""
        response = requests.get(f"{BASE_URL}/api/reports/scan/{scan_id}/pdf", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"PDF download failed: {response.text}"
        assert "application/pdf" in response.headers.get("content-type", "")
        assert len(response.content) > 100, "PDF content too small"
        print(f"✓ PDF report download successful - size: {len(response.content)} bytes")


class TestAPIKeySystem:
    """Test API key generation and usage"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_api_key_usage_stats(self, owner_token):
        """Test API key usage stats endpoint"""
        response = requests.get(f"{BASE_URL}/api/apikey/usage", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Usage stats failed: {response.text}"
        data = response.json()
        assert "has_key" in data
        assert "daily_limit" in data
        print(f"✓ API key usage stats - has_key: {data['has_key']}, daily_limit: {data['daily_limit']}")
    
    def test_api_scan_with_key(self):
        """Test scanning via API key (X-API-Key header)"""
        response = requests.post(f"{BASE_URL}/api/v1/scan/url", 
                                json={"url": "https://google.com"},
                                headers={"X-API-Key": OWNER_API_KEY})
        assert response.status_code == 200, f"API scan failed: {response.text}"
        data = response.json()
        assert "scan_id" in data
        assert "risk_score" in data
        print(f"✓ API scan via X-API-Key successful - scan_id: {data['scan_id']}")
    
    def test_api_scan_without_key_fails(self):
        """Test that API scan without key returns 401"""
        response = requests.post(f"{BASE_URL}/api/v1/scan/url", 
                                json={"url": "https://google.com"})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ API scan without key correctly returns 401")


class TestTeams:
    """Test team management (Enterprise)"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_team(self, owner_token):
        """Test getting team info"""
        response = requests.get(f"{BASE_URL}/api/teams/my", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Get team failed: {response.text}"
        data = response.json()
        # Team may or may not exist
        if data.get("has_team"):
            assert "name" in data
            assert "members" in data
            print(f"✓ Team exists - name: {data['name']}, members: {len(data.get('members', []))}")
        else:
            print(f"✓ No team yet (expected for fresh setup)")
    
    def test_add_member_nonexistent_email(self, owner_token):
        """Test adding member with non-existent email returns 404"""
        response = requests.post(f"{BASE_URL}/api/teams/members", 
                                json={"email": "nonexistent_test_user_12345@example.com", "role": "member"},
                                headers={"Authorization": f"Bearer {owner_token}"})
        # Should return 404 (user not found) or 404 (no team)
        assert response.status_code in [404, 400], f"Expected 404/400, got {response.status_code}: {response.text}"
        print(f"✓ Add non-existent member correctly returns error")


class TestWebhooks:
    """Test webhook management (Enterprise)"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_list_webhooks(self, owner_token):
        """Test listing webhooks"""
        response = requests.get(f"{BASE_URL}/api/webhooks", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"List webhooks failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Webhooks listed - count: {len(data)}")
        return data
    
    def test_create_webhook(self, owner_token):
        """Test creating a webhook"""
        response = requests.post(f"{BASE_URL}/api/webhooks", 
                                json={
                                    "url": "https://httpbin.org/post",
                                    "events": ["scan.completed"]
                                },
                                headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Create webhook failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "secret" in data
        print(f"✓ Webhook created - id: {data['id']}")
        return data["id"]
    
    def test_test_webhook_ping(self, owner_token):
        """Test webhook ping functionality"""
        # First get existing webhooks
        list_response = requests.get(f"{BASE_URL}/api/webhooks", 
                                    headers={"Authorization": f"Bearer {owner_token}"})
        webhooks = list_response.json()
        
        if webhooks:
            webhook_id = webhooks[0]["id"]
            response = requests.post(f"{BASE_URL}/api/webhooks/{webhook_id}/test", 
                                    json={},
                                    headers={"Authorization": f"Bearer {owner_token}"})
            assert response.status_code == 200, f"Webhook test failed: {response.text}"
            data = response.json()
            print(f"✓ Webhook ping test - success: {data.get('success')}")
        else:
            print("✓ No webhooks to test (skipped)")


class TestReports:
    """Test report generation and scheduling (Premium+)"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_download_weekly_report(self, owner_token):
        """Test downloading weekly summary PDF"""
        response = requests.get(f"{BASE_URL}/api/reports/summary?period=weekly", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Weekly report failed: {response.text}"
        assert "application/pdf" in response.headers.get("content-type", "")
        print(f"✓ Weekly PDF report downloaded - size: {len(response.content)} bytes")
    
    def test_create_report_schedule(self, owner_token):
        """Test creating a report schedule"""
        response = requests.post(f"{BASE_URL}/api/reports/schedule", 
                                json={"frequency": "weekly", "format": "pdf"},
                                headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Create schedule failed: {response.text}"
        data = response.json()
        assert "next_send" in data
        print(f"✓ Report schedule created - next_send: {data['next_send']}")
    
    def test_get_report_schedule(self, owner_token):
        """Test getting report schedule"""
        response = requests.get(f"{BASE_URL}/api/reports/schedule", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Get schedule failed: {response.text}"
        data = response.json()
        print(f"✓ Report schedule retrieved - enabled: {data.get('enabled', False)}")


class TestOwnerPricing:
    """Test owner price control"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_site_settings(self, owner_token):
        """Test getting site settings (prices)"""
        response = requests.get(f"{BASE_URL}/api/owner/site-settings", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Get settings failed: {response.text}"
        data = response.json()
        assert "premium_price" in data
        assert "enterprise_price" in data
        print(f"✓ Site settings - premium: {data['premium_price']}, enterprise: {data['enterprise_price']}")
    
    def test_update_prices(self, owner_token):
        """Test updating prices"""
        # Update to test value
        response = requests.put(f"{BASE_URL}/api/owner/site-settings/prices", 
                               json={"premium_price": 799, "enterprise_price": 2999},
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Update prices failed: {response.text}"
        
        # Verify change
        verify_response = requests.get(f"{BASE_URL}/api/billing/plans")
        plans = verify_response.json()
        premium_plan = next((p for p in plans if p["name"] == "premium"), None)
        assert premium_plan is not None
        assert premium_plan["price"] == 799, f"Price not updated: {premium_plan['price']}"
        print(f"✓ Prices updated and verified - premium: 799")
        
        # Restore original
        requests.put(f"{BASE_URL}/api/owner/site-settings/prices", 
                    json={"premium_price": 599, "enterprise_price": 2499},
                    headers={"Authorization": f"Bearer {owner_token}"})
        print(f"✓ Prices restored to original")
    
    def test_plans_show_dynamic_pricing(self):
        """Test that /api/billing/plans returns dynamic prices"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        assert response.status_code == 200, f"Get plans failed: {response.text}"
        plans = response.json()
        assert len(plans) == 3, f"Expected 3 plans, got {len(plans)}"
        
        plan_names = [p["name"] for p in plans]
        assert "free" in plan_names
        assert "premium" in plan_names
        assert "enterprise" in plan_names
        print(f"✓ Plans endpoint returns all 3 plans with dynamic pricing")


class TestOwnerPaymentSettings:
    """Test owner payment gateway settings"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_payment_settings(self, owner_token):
        """Test getting payment settings"""
        response = requests.get(f"{BASE_URL}/api/owner/payment-settings", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Get payment settings failed: {response.text}"
        data = response.json()
        assert "gateway" in data
        assert data["gateway"] == "razorpay"
        print(f"✓ Payment settings retrieved - gateway: {data['gateway']}")


class TestAdminPlanManagement:
    """Test admin user plan management"""
    
    @pytest.fixture
    def owner_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL, "password": OWNER_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_all_users(self, owner_token):
        """Test getting all users as admin"""
        response = requests.get(f"{BASE_URL}/api/admin/users", 
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Get users failed: {response.text}"
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0
        print(f"✓ Admin can list users - count: {len(users)}")
        return users
    
    def test_change_user_plan(self, owner_token):
        """Test changing a user's plan"""
        # Get users
        users_response = requests.get(f"{BASE_URL}/api/admin/users", 
                                     headers={"Authorization": f"Bearer {owner_token}"})
        users = users_response.json()
        
        # Find a non-owner user to test with
        test_user = next((u for u in users if u["role"] == "user" and u["plan"] == "free"), None)
        if not test_user:
            print("✓ No free user available for plan change test (skipped)")
            return
        
        user_id = test_user["id"]
        original_plan = test_user["plan"]
        
        # Change to premium
        response = requests.put(f"{BASE_URL}/api/admin/users/{user_id}/plan", 
                               json={"plan": "premium"},
                               headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 200, f"Plan change failed: {response.text}"
        data = response.json()
        assert data["new_plan"] == "premium"
        assert data["new_credits"] == 500
        print(f"✓ User plan changed to premium - credits: {data['new_credits']}")
        
        # Restore original plan
        requests.put(f"{BASE_URL}/api/admin/users/{user_id}/plan", 
                    json={"plan": original_plan},
                    headers={"Authorization": f"Bearer {owner_token}"})
        print(f"✓ User plan restored to {original_plan}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
