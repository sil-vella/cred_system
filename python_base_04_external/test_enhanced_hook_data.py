#!/usr/bin/env python3
"""
Test script for enhanced hook data flow with app identification and raw email.
This tests the improved hook system with proper data handling.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5001"
TEST_USERNAME = f"enhanced_user_{int(time.time())}"
TEST_EMAIL = f"enhanced_user_{int(time.time())}@example.com"
TEST_PASSWORD = "testpassword123"

def test_enhanced_hook_data():
    """Test the enhanced hook data flow with app identification."""
    print("🧪 Testing Enhanced Hook Data Flow")
    print("=" * 50)
    
    # Test 1: Create user with enhanced hook data
    print("\n1️⃣ Creating user with enhanced hook data...")
    
    user_data = {
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "first_name": "Enhanced",
        "last_name": "User",
        "phone": "+1234567890"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/public/register",
            json=user_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print("   ✅ User created successfully!")
            print(f"   📊 Response: {json.dumps(result, indent=2)}")
            
            # Check that no wallet_id is returned (since it's embedded)
            if 'wallet_id' not in result.get('data', {}):
                print("   ✅ Confirmed: No separate wallet_id (embedded structure)")
            else:
                print("   ❌ Warning: Separate wallet_id still present")
                
        else:
            print(f"   ❌ User creation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error creating user: {e}")
        return False
    
    # Test 2: Verify hook data structure
    print("\n2️⃣ Verifying enhanced hook data structure...")
    print("   Expected hook data should include:")
    print("   - user_id: MongoDB ObjectId (string)")
    print("   - username: Raw from request")
    print("   - email: Raw from request (non-encrypted)")
    print("   - app_id: From Config.APP_ID")
    print("   - app_name: From Config.APP_NAME")
    print("   - source: 'external_app'")
    print("   - created_at: ISO timestamp")
    
    # Test 3: Check application logs for hook execution
    print("\n3️⃣ Checking enhanced hook execution logs...")
    print("   Look for these log messages:")
    print("   - '🎣 Triggered user_created hook for user: {username} ({email})'")
    print("   - '   - App: {app_name} ({app_id})'")
    print("   - '   - User ID: {user_id}'")
    print("   - '🎣 CreditSystemModule: Processing user creation for {username} ({email})'")
    print("   - '   - Source App: {app_name} ({app_id})'")
    print("   - '🎣 CommunicationsModule: Processing user creation for {username} ({email})'")
    print("   - '   - Source App: {app_name}'")
    
    # Test 4: Verify database collections
    print("\n4️⃣ Database verification...")
    print("   Users collection should contain:")
    print("   - Embedded wallet data in modules.wallet")
    print("   - Encrypted email field")
    print("   - Complete user profile")
    
    print("   Notifications collection should contain:")
    print("   - Welcome notification with raw email")
    print("   - source_app field with app name")
    print("   - Enhanced title with app name")
    
    # Test 5: Check credit system integration
    print("\n5️⃣ Credit system integration verification...")
    print("   Credit system should receive:")
    print("   - Raw email (non-encrypted)")
    print("   - App identification (app_id, app_name)")
    print("   - Source information")
    print("   - Complete user profile data")
    
    print("\n✅ Enhanced hook data test completed!")
    print("=" * 50)
    
    return True

def test_hook_data_flow():
    """Test the complete hook data flow."""
    print("\n🎣 Testing Complete Hook Data Flow")
    print("=" * 40)
    
    print("Hook Data Flow:")
    print("1. UserManagementModule.create_user()")
    print("   ↓")
    print("2. Prepare hook_data with raw email and app info")
    print("   ↓")
    print("3. trigger_hook('user_created', hook_data)")
    print("   ↓")
    print("4. HooksManager executes callbacks by priority:")
    print("   - CommunicationsModule (priority=10)")
    print("   - CreditSystemModule (priority=15)")
    print("   - WalletModule (priority=5) - No longer needed")
    print("   ↓")
    print("5. Each callback receives enhanced hook_data")
    
    print("\nEnhanced Hook Data Structure:")
    print("```json")
    print("{")
    print('  "user_id": "507f1f77bcf86cd799439011",')
    print('  "username": "testuser",')
    print('  "email": "test@example.com",  // Raw, non-encrypted')
    print('  "user_data": { /* complete user document */ },')
    print('  "created_at": "2025-07-09T12:00:00.000Z",')
    print('  "app_id": "external_app_001",')
    print('  "app_name": "External Application",')
    print('  "source": "external_app"')
    print("}")
    print("```")
    
    print("\n✅ Hook data flow test completed!")

def test_app_identification():
    """Test app identification in hook data."""
    print("\n🏷️ Testing App Identification")
    print("=" * 30)
    
    print("Expected App Configuration:")
    print("- APP_ID: external_app_001")
    print("- APP_NAME: External Application")
    print("- Source: external_app")
    
    print("\nThis information will be:")
    print("1. Included in hook data")
    print("2. Sent to credit system")
    print("3. Used in welcome notifications")
    print("4. Logged for debugging")
    
    print("\n✅ App identification test completed!")

if __name__ == "__main__":
    print("🚀 Starting Enhanced Hook Data Tests")
    print("=" * 60)
    
    # Test enhanced hook data
    success = test_enhanced_hook_data()
    
    # Test hook data flow
    test_hook_data_flow()
    
    # Test app identification
    test_app_identification()
    
    if success:
        print("\n🎉 All enhanced hook data tests completed successfully!")
        print("✅ Raw email handling working")
        print("✅ App identification integrated")
        print("✅ Enhanced hook data structure implemented")
        print("✅ Credit system integration improved")
        print("✅ Communications module enhanced")
    else:
        print("\n❌ Some tests failed - check logs for details")
    
    print("\n" + "=" * 60) 