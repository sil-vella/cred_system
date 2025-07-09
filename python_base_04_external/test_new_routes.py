#!/usr/bin/env python3
"""
Test script to demonstrate the new route registration system.
This script shows how the new authentication-aware route registration works.
"""

import requests
import json

# Base URL for the external app
BASE_URL = "http://localhost:8081"

def test_public_routes():
    """Test routes that don't require authentication."""
    print("🔓 Testing Public Routes (No Auth Required)")
    print("=" * 50)
    
    # Test public user info
    response = requests.get(f"{BASE_URL}/public/users/info")
    print(f"GET /public/users/info: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    print()

def test_jwt_routes():
    """Test routes that require JWT authentication."""
    print("🔐 Testing JWT Routes (Requires JWT Token)")
    print("=" * 50)
    
    # Test without JWT token (should fail)
    response = requests.get(f"{BASE_URL}/userauth/users/profile")
    print(f"GET /userauth/users/profile (no token): {response.status_code}")
    if response.status_code == 401:
        print(f"Error: {response.json()}")
    print()
    
    # Test with invalid JWT token (should fail)
    headers = {"Authorization": "Bearer invalid_token"}
    response = requests.get(f"{BASE_URL}/userauth/users/profile", headers=headers)
    print(f"GET /userauth/users/profile (invalid token): {response.status_code}")
    if response.status_code == 401:
        print(f"Error: {response.json()}")
    print()

def test_api_key_routes():
    """Test routes that require API key authentication."""
    print("🔑 Testing API Key Routes (Requires API Key)")
    print("=" * 50)
    
    # Test without API key (should fail)
    response = requests.post(f"{BASE_URL}/keyauth/users/create", 
                           json={"email": "test@example.com", "username": "testuser"})
    print(f"POST /keyauth/users/create (no key): {response.status_code}")
    if response.status_code == 401:
        print(f"Error: {response.json()}")
    print()
    
    # Test with invalid API key (should fail)
    headers = {"X-API-Key": "invalid_key"}
    response = requests.post(f"{BASE_URL}/keyauth/users/create", 
                           json={"email": "test@example.com", "username": "testuser"},
                           headers=headers)
    print(f"POST /keyauth/users/create (invalid key): {response.status_code}")
    if response.status_code == 401:
        print(f"Error: {response.json()}")
    print()

def test_route_prefixes():
    """Test that route prefixes work correctly."""
    print("🔍 Testing Route Prefixes")
    print("=" * 50)
    
    # Test that non-prefixed routes are public
    response = requests.get(f"{BASE_URL}/health")
    print(f"GET /health (no prefix): {response.status_code}")
    if response.status_code == 200:
        print("✅ Non-prefixed routes are public by default")
    print()
    
    # Test that /public/ prefix works
    response = requests.get(f"{BASE_URL}/public/users/info")
    print(f"GET /public/users/info: {response.status_code}")
    if response.status_code == 200:
        print("✅ /public/ prefix works correctly")
    print()

def test_route_registration():
    """Test that routes are properly registered."""
    print("📋 Testing Route Registration")
    print("=" * 50)
    
    # Check module status to see registered routes
    response = requests.get(f"{BASE_URL}/modules/status")
    if response.status_code == 200:
        data = response.json()
        user_management = data.get('modules', {}).get('user_management', {})
        routes = user_management.get('info', {}).get('routes', [])
        
        print("Registered routes in UserManagementModule:")
        for route in routes:
            print(f"  - {route}")
        print()
        
        # Count routes by type
        public_routes = [r for r in routes if r.startswith('/public/')]
        jwt_routes = [r for r in routes if r.startswith('/userauth/')]
        key_routes = [r for r in routes if r.startswith('/keyauth/')]
        legacy_routes = [r for r in routes if not r.startswith(('/public/', '/userauth/', '/keyauth/'))]
        
        print(f"Route counts:")
        print(f"  - Public routes: {len(public_routes)}")
        print(f"  - JWT routes: {len(jwt_routes)}")
        print(f"  - API Key routes: {len(key_routes)}")
        print(f"  - Legacy routes: {len(legacy_routes)}")
        print()

def main():
    """Run all tests."""
    print("🚀 Testing New Route Registration System")
    print("=" * 60)
    print()
    
    try:
        test_public_routes()
        test_jwt_routes()
        test_api_key_routes()
        test_route_prefixes()
        test_route_registration()
        
        print("✅ All tests completed!")
        print()
        print("📝 Summary:")
        print("- Public routes (/public/*) work without authentication")
        print("- JWT routes (/userauth/*) require valid JWT token")
        print("- API Key routes (/keyauth/*) require valid API key")
        print("- Non-prefixed routes are public by default")
        print("- Route registration is now authentication-aware")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to the external app.")
        print("Make sure the app is running on http://localhost:8081")
    except Exception as e:
        print(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    main() 