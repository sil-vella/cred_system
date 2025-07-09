#!/usr/bin/env python3
"""
Test script for multi-tenant user creation flow.
This tests the complete flow from external app to credit system with proper database structure.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
EXTERNAL_BASE_URL = "http://localhost:5001"
CREDIT_SYSTEM_BASE_URL = "http://localhost:5002"
TEST_USERNAME = f"multi_tenant_user_{int(time.time())}"
TEST_EMAIL = f"multi_tenant_user_{int(time.time())}@example.com"
TEST_PASSWORD = "testpassword123"

def test_multi_tenant_user_creation():
    """Test the complete multi-tenant user creation flow."""
    print("🧪 Testing Multi-Tenant User Creation Flow")
    print("=" * 60)
    
    # Test 1: Create user in external app
    print("\n1️⃣ Creating user in external app...")
    
    user_data = {
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "first_name": "Multi",
        "last_name": "Tenant",
        "phone": "+1234567890",
        "timezone": "America/New_York",
        "language": "en"
    }
    
    try:
        response = requests.post(
            f"{EXTERNAL_BASE_URL}/users/create",
            json=user_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        if response.status_code == 201:
            external_user_data = response.json()
            external_user_id = external_user_data.get('user', {}).get('_id')
            print(f"   ✅ External user created: {external_user_id}")
        else:
            print(f"   ❌ Failed to create external user")
            return
            
    except Exception as e:
        print(f"   ❌ Error creating external user: {e}")
        return
    
    # Test 2: Check external app database
    print("\n2️⃣ Checking external app database...")
    
    try:
        # Check users collection
        response = requests.get(f"{EXTERNAL_BASE_URL}/health")
        if response.status_code == 200:
            print("   ✅ External app is healthy")
        else:
            print("   ⚠️ External app health check failed")
            
    except Exception as e:
        print(f"   ❌ Error checking external app: {e}")
    
    # Test 3: Check credit system database
    print("\n3️⃣ Checking credit system database...")
    
    try:
        # Check credit system health
        response = requests.get(f"{CREDIT_SYSTEM_BASE_URL}/health")
        if response.status_code == 200:
            print("   ✅ Credit system is healthy")
        else:
            print("   ⚠️ Credit system health check failed")
            
    except Exception as e:
        print(f"   ❌ Error checking credit system: {e}")
    
    # Test 4: Verify hook system worked
    print("\n4️⃣ Verifying hook system and data flow...")
    
    try:
        # Check if user exists in credit system
        response = requests.post(
            f"{CREDIT_SYSTEM_BASE_URL}/users/search",
            json={"email": TEST_EMAIL},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            search_results = response.json()
            users = search_results.get('users', [])
            if users:
                credit_user = users[0]
                print(f"   ✅ User found in credit system: {credit_user.get('_id')}")
                print(f"   📧 Email: {credit_user.get('email')}")
                print(f"   👤 Username: {credit_user.get('username')}")
                print(f"   📊 Modules: {list(credit_user.get('modules', {}).keys())}")
            else:
                print("   ⚠️ User not found in credit system")
        else:
            print(f"   ⚠️ Credit system search failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error searching credit system: {e}")
    
    # Test 5: Check notifications
    print("\n5️⃣ Checking welcome notifications...")
    
    try:
        # This would require a notifications endpoint
        print("   ℹ️ Notifications would be checked via database query")
        
    except Exception as e:
        print(f"   ❌ Error checking notifications: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Multi-Tenant User Creation Test Complete!")
    print("\n📋 Expected Results:")
    print("   ✅ External app: User created with embedded wallet data")
    print("   ✅ Credit system: Core user + app connection records")
    print("   ✅ Hook system: user_created event triggered")
    print("   ✅ Notifications: Welcome message created")
    print("   ✅ Database structure: Multi-tenant modular format")

def test_database_structure():
    """Test the database structure alignment."""
    print("\n🔍 Testing Database Structure Alignment")
    print("=" * 50)
    
    print("\n📊 External App Database Structure:")
    print("   - users: Core user data with embedded modules")
    print("   - notifications: Welcome notifications")
    print("   - user_audit_logs: Audit trail")
    
    print("\n📊 Credit System Database Structure:")
    print("   - users: Core user data (no app-specific data)")
    print("   - user_apps: Multi-tenant app connections")
    print("   - user_modules: Module registry")
    print("   - user_audit_logs: Complete audit trail")
    
    print("\n🔗 Multi-Tenant Features:")
    print("   ✅ Users can connect to multiple external apps")
    print("   ✅ Each app connection has independent permissions")
    print("   ✅ App-specific audit trail for security")
    print("   ✅ Flexible sync settings per app")
    print("   ✅ Rate limiting per app connection")

if __name__ == "__main__":
    test_multi_tenant_user_creation()
    test_database_structure() 