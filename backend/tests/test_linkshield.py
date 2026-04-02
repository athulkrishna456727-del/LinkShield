"""
Link Shield Backend API Tests
Tests: Auth (signup/login), Dashboard, URL Scan, Role Access (Admin/Owner), Plans, Payment
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://linkshield-demo.preview.emergentagent.com')

# Test credentials from requirements
OWNER_EMAIL = "athulkrishna456727@gmail.com"
OWNER_PASSWORD = "#AThr401012#"
ADMIN_EMAIL = "athulmark401012@gmail.com"
ADMIN_PASSWORD = "dgskgsnskz"

class TestAuthSignup:
    """Test signup flow - Feature 1"""
    
    def test_signup_new_user_success(self):
        """Create new user with email, password, name, username"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "email": f"test_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "E2E Test User",
            "username": f"testuser_{unique_id}"
        }
        response = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        assert response.status_code == 200, f"Signup failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Token not returned"
        assert "user" in data, "User not returned"
        assert data["user"]["email"] == payload["email"]
        assert data["user"]["plan"] == "free", "Default plan should be free"
        assert data["user"]["credits"] == 50, "Default credits should be 50"
        assert data["user"]["role"] == "user", "Default role should be user"
        print(f"✓ Signup successful: {payload['email']}")
    
    def test_signup_duplicate_email_rejected(self):
        """Test duplicate email rejection"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "email": f"dup_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "Dup Test",
            "username": f"dupuser_{unique_id}"
        }
        # First signup
        response1 = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        assert response1.status_code == 200
        
        # Second signup with same email
        payload["username"] = f"dupuser2_{unique_id}"
        response2 = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        assert response2.status_code == 400, "Duplicate email should be rejected"
        assert "already registered" in response2.json().get("detail", "").lower()
        print("✓ Duplicate email correctly rejected")
    
    def test_signup_duplicate_username_rejected(self):
        """Test duplicate username rejection"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "email": f"user1_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "User 1",
            "username": f"sameuser_{unique_id}"
        }
        # First signup
        response1 = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        assert response1.status_code == 200
        
        # Second signup with same username
        payload["email"] = f"user2_{unique_id}@example.com"
        response2 = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        assert response2.status_code == 400, "Duplicate username should be rejected"
        assert "username already taken" in response2.json().get("detail", "").lower()
        print("✓ Duplicate username correctly rejected")
    
    def test_signup_invalid_username_format_rejected(self):
        """Test invalid username format rejection"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "email": f"invalid_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "Invalid User",
            "username": "ab"  # Too short
        }
        response = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        assert response.status_code == 400, "Short username should be rejected"
        print("✓ Invalid username format correctly rejected")


class TestAuthLogin:
    """Test login flow - Feature 2"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user for login tests"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "email": f"login_test_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "Login Test",
            "username": f"logintest_{unique_id}"
        }
        response = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        assert response.status_code == 200
        return payload
    
    def test_login_success(self, test_user):
        """Test successful login returns token + user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"]
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "Token not returned"
        assert "user" in data, "User not returned"
        assert data["user"]["email"] == test_user["email"]
        print(f"✓ Login successful for {test_user['email']}")
    
    def test_login_invalid_credentials(self):
        """Test invalid credentials return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, "Invalid credentials should return 401"
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_jwt_token_valid_for_me_endpoint(self, test_user):
        """Test JWT token can fetch /api/auth/me"""
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"]
        })
        token = login_response.json()["token"]
        
        # Use token to fetch /api/auth/me
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert me_response.status_code == 200, f"Failed to fetch /api/auth/me: {me_response.text}"
        
        data = me_response.json()
        assert data["email"] == test_user["email"]
        print("✓ JWT token valid for /api/auth/me")


class TestDashboard:
    """Test dashboard flow - Feature 3"""
    
    @pytest.fixture
    def authenticated_user(self):
        """Create and login a test user"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "email": f"dash_test_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "Dashboard Test",
            "username": f"dashtest_{unique_id}"
        }
        signup_response = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        assert signup_response.status_code == 200
        return signup_response.json()
    
    def test_user_stats_endpoint(self, authenticated_user):
        """Test user stats endpoint"""
        token = authenticated_user["token"]
        response = requests.get(f"{BASE_URL}/api/user/stats", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "total_scans" in data
        assert "malicious" in data
        assert "suspicious" in data
        assert "safe" in data
        print("✓ User stats endpoint working")
    
    def test_scan_history_endpoint(self, authenticated_user):
        """Test scan history endpoint"""
        token = authenticated_user["token"]
        response = requests.get(f"{BASE_URL}/api/scan/history/list", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print("✓ Scan history endpoint working")


class TestURLScan:
    """Test URL scan - Feature 4"""
    
    @pytest.fixture
    def authenticated_user(self):
        """Create and login a test user"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "email": f"scan_test_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "Scan Test",
            "username": f"scantest_{unique_id}"
        }
        signup_response = requests.post(f"{BASE_URL}/api/auth/signup", json=payload)
        assert signup_response.status_code == 200
        return signup_response.json()
    
    def test_url_scan_success(self, authenticated_user):
        """Test URL scan returns result with risk score, level, metadata, IOCs"""
        token = authenticated_user["token"]
        initial_credits = authenticated_user["user"]["credits"]
        
        response = requests.post(f"{BASE_URL}/api/scan/url", 
            json={"url": "https://example.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"URL scan failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Scan ID not returned"
        assert "risk_score" in data, "Risk score not returned"
        assert "risk_level" in data, "Risk level not returned"
        assert "metadata" in data, "Metadata not returned"
        assert "iocs" in data, "IOCs not returned"
        assert data["risk_level"] in ["safe", "suspicious", "malicious"]
        assert "credits_used" in data, "Credits used not returned"
        print(f"✓ URL scan successful - Risk: {data['risk_level']}, Score: {data['risk_score']}")
        
        # Verify credits deducted
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        new_credits = me_response.json()["credits"]
        assert new_credits < initial_credits, "Credits should be deducted after scan"
        print(f"✓ Credits deducted: {initial_credits} -> {new_credits}")
        
        return data["id"]
    
    def test_scan_appears_in_history(self, authenticated_user):
        """Test scan appears in history"""
        token = authenticated_user["token"]
        
        # Perform a scan
        scan_response = requests.post(f"{BASE_URL}/api/scan/url", 
            json={"url": "https://test-history.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        scan_id = scan_response.json()["id"]
        
        # Check history
        history_response = requests.get(f"{BASE_URL}/api/scan/history/list", headers={
            "Authorization": f"Bearer {token}"
        })
        assert history_response.status_code == 200
        
        history = history_response.json()
        scan_ids = [s["id"] for s in history]
        assert scan_id in scan_ids, "Scan should appear in history"
        print("✓ Scan appears in history")
    
    def test_get_scan_result_by_id(self, authenticated_user):
        """Test getting scan result by ID"""
        token = authenticated_user["token"]
        
        # Perform a scan
        scan_response = requests.post(f"{BASE_URL}/api/scan/url", 
            json={"url": "https://get-by-id-test.com"},
            headers={"Authorization": f"Bearer {token}"}
        )
        scan_id = scan_response.json()["id"]
        
        # Get scan by ID
        result_response = requests.get(f"{BASE_URL}/api/scan/{scan_id}", headers={
            "Authorization": f"Bearer {token}"
        })
        assert result_response.status_code == 200
        
        data = result_response.json()
        assert data["id"] == scan_id
        assert "risk_score" in data
        assert "risk_level" in data
        print("✓ Get scan result by ID working")


class TestAdminAccess:
    """Test admin role access - Feature 5"""
    
    def test_admin_login_and_dashboard_access(self):
        """Login as admin and verify admin dashboard access"""
        # Login as admin
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        
        token = login_response.json()["token"]
        user = login_response.json()["user"]
        assert user["role"] in ["admin", "owner"], f"Expected admin/owner role, got {user['role']}"
        print(f"✓ Admin login successful - Role: {user['role']}")
        
        # Test admin endpoints
        users_response = requests.get(f"{BASE_URL}/api/admin/users", headers={
            "Authorization": f"Bearer {token}"
        })
        assert users_response.status_code == 200, "Admin users endpoint failed"
        print("✓ Admin users endpoint accessible")
        
        scans_response = requests.get(f"{BASE_URL}/api/admin/scans?limit=10", headers={
            "Authorization": f"Bearer {token}"
        })
        assert scans_response.status_code == 200, "Admin scans endpoint failed"
        print("✓ Admin scans endpoint accessible")
        
        analytics_response = requests.get(f"{BASE_URL}/api/admin/analytics/detailed", headers={
            "Authorization": f"Bearer {token}"
        })
        assert analytics_response.status_code == 200, "Admin analytics endpoint failed"
        print("✓ Admin analytics endpoint accessible")


class TestOwnerAccess:
    """Test owner role access - Feature 6 & 7"""
    
    def test_owner_login_and_controls_access(self):
        """Login as owner and verify owner controls access"""
        # Login as owner
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        assert login_response.status_code == 200, f"Owner login failed: {login_response.text}"
        
        token = login_response.json()["token"]
        user = login_response.json()["user"]
        assert user["role"] == "owner", f"Expected owner role, got {user['role']}"
        print(f"✓ Owner login successful - Role: {user['role']}")
        
        # Test owner endpoints
        admins_response = requests.get(f"{BASE_URL}/api/owner/admins", headers={
            "Authorization": f"Bearer {token}"
        })
        assert admins_response.status_code == 200, "Owner admins endpoint failed"
        print("✓ Owner admins endpoint accessible")
        
        audit_response = requests.get(f"{BASE_URL}/api/owner/audit-logs?limit=10", headers={
            "Authorization": f"Bearer {token}"
        })
        assert audit_response.status_code == 200, "Owner audit logs endpoint failed"
        print("✓ Owner audit logs endpoint accessible")
        
        system_response = requests.get(f"{BASE_URL}/api/owner/system-settings", headers={
            "Authorization": f"Bearer {token}"
        })
        assert system_response.status_code == 200, "Owner system settings endpoint failed"
        print("✓ Owner system settings endpoint accessible")
    
    def test_owner_create_admin(self):
        """Test owner can create admin"""
        # Login as owner
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OWNER_EMAIL,
            "password": OWNER_PASSWORD
        })
        token = login_response.json()["token"]
        
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(f"{BASE_URL}/api/owner/create-admin", 
            json={
                "email": f"newadmin_{unique_id}@example.com",
                "name": "New Admin",
                "temporary_password": "TempPass123"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert create_response.status_code == 200, f"Create admin failed: {create_response.text}"
        print("✓ Owner can create admin")


class TestPlans:
    """Test plans page - Feature 8"""
    
    def test_get_plans(self):
        """Test plans endpoint returns 3 plans"""
        response = requests.get(f"{BASE_URL}/api/billing/plans")
        assert response.status_code == 200
        
        plans = response.json()
        assert len(plans) == 3, f"Expected 3 plans, got {len(plans)}"
        
        plan_names = [p["name"] for p in plans]
        assert "free" in plan_names
        assert "premium" in plan_names
        assert "enterprise" in plan_names
        
        # Verify pricing
        for plan in plans:
            if plan["name"] == "free":
                assert plan["price"] == 0
                assert plan["credits_per_month"] == 50
            elif plan["name"] == "premium":
                assert plan["price"] == 499
                assert plan["credits_per_month"] == 500
            elif plan["name"] == "enterprise":
                assert plan["price"] == 2499
        
        print("✓ Plans endpoint returns correct data")


class TestPaymentFlow:
    """Test payment flow - Feature 9"""
    
    def test_create_order_fails_with_demo_keys(self):
        """Test create-order fails gracefully with demo Razorpay keys"""
        # Create a test user
        unique_id = str(uuid.uuid4())[:8]
        signup_response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "email": f"payment_test_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "Payment Test",
            "username": f"paytest_{unique_id}"
        })
        token = signup_response.json()["token"]
        
        # Try to create order - should fail with demo keys
        order_response = requests.post(f"{BASE_URL}/api/billing/create-order",
            json={"plan": "premium"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # With demo keys, this should return 500 error
        assert order_response.status_code == 500, f"Expected 500 with demo keys, got {order_response.status_code}"
        assert "Failed to create order" in order_response.json().get("detail", "")
        print("✓ Payment create-order fails gracefully with demo keys (expected behavior)")


class TestRegularUserCannotAccessAdmin:
    """Test regular user cannot access admin endpoints"""
    
    def test_regular_user_blocked_from_admin(self):
        """Regular user should get 403 on admin endpoints"""
        # Create regular user
        unique_id = str(uuid.uuid4())[:8]
        signup_response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "email": f"regular_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "Regular User",
            "username": f"regular_{unique_id}"
        })
        token = signup_response.json()["token"]
        
        # Try admin endpoint
        admin_response = requests.get(f"{BASE_URL}/api/admin/users", headers={
            "Authorization": f"Bearer {token}"
        })
        assert admin_response.status_code == 403, "Regular user should be blocked from admin"
        print("✓ Regular user correctly blocked from admin endpoints")
    
    def test_regular_user_blocked_from_owner(self):
        """Regular user should get 403 on owner endpoints"""
        # Create regular user
        unique_id = str(uuid.uuid4())[:8]
        signup_response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "email": f"regular2_{unique_id}@example.com",
            "password": "TestPass123",
            "name": "Regular User 2",
            "username": f"regular2_{unique_id}"
        })
        token = signup_response.json()["token"]
        
        # Try owner endpoint
        owner_response = requests.get(f"{BASE_URL}/api/owner/admins", headers={
            "Authorization": f"Bearer {token}"
        })
        assert owner_response.status_code == 403, "Regular user should be blocked from owner"
        print("✓ Regular user correctly blocked from owner endpoints")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
