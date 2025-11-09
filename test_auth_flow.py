#!/usr/bin/env python3
"""
Test authentication flow end-to-end
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "https://code-explorer-107.preview.emergentagent.com/api/auth"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health():
    """Test if backend is healthy"""
    print_section("Testing Backend Health")
    try:
        response = requests.get("https://code-explorer-107.preview.emergentagent.com/api/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is healthy")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_registration(username, email, password):
    """Test user registration"""
    print_section(f"Testing Registration: {username}")
    try:
        response = requests.post(
            f"{BASE_URL}/register",
            json={
                "username": username,
                "email": email,
                "password": password
            },
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Registration successful!")
            print(f"   Access Token: {data['access_token'][:50]}...")
            print(f"   Refresh Token: {data['refresh_token'][:50]}...")
            print(f"   Token Type: {data['token_type']}")
            return data
        else:
            print(f"❌ Registration failed with status {response.status_code}")
            print(f"   Error: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None

def test_login(email, password):
    """Test user login"""
    print_section(f"Testing Login: {email}")
    try:
        response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": email,
                "password": password
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"   Access Token: {data['access_token'][:50]}...")
            print(f"   Refresh Token: {data['refresh_token'][:50]}...")
            return data
        else:
            print(f"❌ Login failed with status {response.status_code}")
            print(f"   Error: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_get_user(access_token):
    """Test getting current user"""
    print_section("Testing Get Current User")
    try:
        response = requests.get(
            f"{BASE_URL}/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ User data retrieved successfully!")
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"❌ Get user failed with status {response.status_code}")
            print(f"   Error: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Get user error: {e}")
        return None

def test_refresh_token(refresh_token):
    """Test token refresh"""
    print_section("Testing Token Refresh")
    try:
        response = requests.post(
            f"{BASE_URL}/refresh",
            json={
                "refresh_token": refresh_token
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Token refresh successful!")
            print(f"   New Access Token: {data['access_token'][:50]}...")
            return data
        else:
            print(f"❌ Token refresh failed with status {response.status_code}")
            print(f"   Error: {response.json()}")
            return None
    except Exception as e:
        print(f"❌ Token refresh error: {e}")
        return None

def test_logout(access_token):
    """Test user logout"""
    print_section("Testing Logout")
    try:
        response = requests.post(
            f"{BASE_URL}/logout",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Logout successful!")
            print(f"   Message: {data['message']}")
            return True
        else:
            print(f"❌ Logout failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Logout error: {e}")
        return False

def test_duplicate_registration(username, email, password):
    """Test that duplicate registration fails"""
    print_section("Testing Duplicate Registration (should fail)")
    try:
        response = requests.post(
            f"{BASE_URL}/register",
            json={
                "username": username,
                "email": email,
                "password": password
            },
            timeout=10
        )
        
        if response.status_code == 400:
            print("✅ Duplicate registration correctly rejected!")
            print(f"   Error message: {response.json()['detail']}")
            return True
        else:
            print(f"❌ Expected 400 but got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Duplicate registration test error: {e}")
        return False

def test_invalid_login():
    """Test that invalid credentials fail"""
    print_section("Testing Invalid Login (should fail)")
    try:
        response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword"
            },
            timeout=10
        )
        
        if response.status_code == 401:
            print("✅ Invalid login correctly rejected!")
            print(f"   Error message: {response.json()['detail']}")
            return True
        else:
            print(f"❌ Expected 401 but got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid login test error: {e}")
        return False

def main():
    """Run all authentication tests"""
    print("\n" + "="*60)
    print("  FILMIT! AUTHENTICATION FLOW TEST")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    # Generate unique test credentials
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    username = f"testuser_{timestamp}"
    email = f"test_{timestamp}@example.com"
    password = "TestPassword123!"
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health()))
    
    # Test 2: Registration
    registration_data = test_registration(username, email, password)
    results.append(("Registration", registration_data is not None))
    
    if registration_data:
        # Test 3: Get current user
        user_data = test_get_user(registration_data['access_token'])
        results.append(("Get User Info", user_data is not None))
        
        # Test 4: Token refresh
        refresh_data = test_refresh_token(registration_data['refresh_token'])
        results.append(("Token Refresh", refresh_data is not None))
        
        # Test 5: Logout
        logout_success = test_logout(registration_data['access_token'])
        results.append(("Logout", logout_success))
    
    # Test 6: Login with same credentials
    login_data = test_login(email, password)
    results.append(("Login", login_data is not None))
    
    # Test 7: Duplicate registration (should fail)
    duplicate_rejected = test_duplicate_registration(username, email, password)
    results.append(("Duplicate Registration Rejection", duplicate_rejected))
    
    # Test 8: Invalid login (should fail)
    invalid_rejected = test_invalid_login()
    results.append(("Invalid Login Rejection", invalid_rejected))
    
    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} tests passed")
    print(f"{'='*60}\n")
    
    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
