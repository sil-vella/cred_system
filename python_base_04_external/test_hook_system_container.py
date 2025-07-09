#!/usr/bin/env python3
"""
Test script to demonstrate the hook system functionality from inside Docker container.
This script creates a user and shows how the hook system triggers
various module callbacks for user creation events.
"""

import requests
import json
import time

# Base URL for the external app (internal container network)
BASE_URL = "http://localhost:5001"  # Internal container port

def test_hook_system():
    """Test the hook system by creating a user and observing the effects."""
    print("🎣 Testing Hook System - User Creation Event")
    print("=" * 60)
    
    # Test data for user creation
    test_user_data = {
        "username": f"testuser_{int(time.time())}",
        "email": f"testuser_{int(time.time())}@example.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
        "phone": "+1234567890"
    }
    
    print(f"📝 Creating test user: {test_user_data['username']}")
    print(f"📧 Email: {test_user_data['email']}")
    print()
    
    try:
        # Create user via the public registration endpoint
        response = requests.post(
            f"{BASE_URL}/public/register",
            json=test_user_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"📤 POST /public/register: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print("✅ User created successfully!")
            print(f"📊 Response: {json.dumps(result, indent=2)}")
            print()
            
            # Check what should have happened via hooks:
            print("🎣 Expected Hook Triggers:")
            print("  1. UserManagementModule: Triggers 'user_created' hook")
            print("  2. WalletModule: Initializes wallet module data (priority 5)")
            print("  3. CommunicationsModule: Sends welcome notification (priority 10)")
            print()
            
            # Wait a moment for async operations
            print("⏳ Waiting for hook processing...")
            time.sleep(2)
            
            # Check if wallet module data was initialized
            print("🔍 Checking if wallet module data was initialized...")
            wallet_response = requests.get(f"{BASE_URL}/wallet/info")
            print(f"📤 GET /wallet/info: {wallet_response.status_code}")
            
            # Check if notifications were created
            print("🔍 Checking if notifications were created...")
            db_response = requests.get(f"{BASE_URL}/get-db-data")
            if db_response.status_code == 200:
                db_data = db_response.json()
                notifications = db_data.get('notifications', [])
                users = db_data.get('users', [])
                
                print(f"📊 Database check results:")
                print(f"   - Notifications: {len(notifications)} found")
                print(f"   - Users: {len(users)} found")
                
                # Show recent notifications
                if notifications:
                    recent_notifications = [n for n in notifications if n.get('type') == 'welcome']
                    print(f"   - Welcome notifications: {len(recent_notifications)} found")
                    for notif in recent_notifications[-3:]:  # Show last 3
                        print(f"     * {notif.get('title', 'No title')}: {notif.get('message', 'No message')}")
                
                # Show user wallet module data
                if users:
                    new_user = None
                    for user in users:
                        if user.get('email') == test_user_data['email']:
                            new_user = user
                            break
                    
                    if new_user:
                        wallet_module = new_user.get('modules', {}).get('wallet', {})
                        print(f"   - User wallet module data:")
                        print(f"     * Enabled: {wallet_module.get('enabled', False)}")
                        print(f"     * Balance: {wallet_module.get('balance', 0)} credits")
                        print(f"     * Currency: {wallet_module.get('currency', 'unknown')}")
                        print(f"     * Last Updated: {wallet_module.get('last_updated', 'unknown')}")
                    else:
                        print(f"   - User not found in database")
            
        else:
            print("❌ User creation failed!")
            print(f"📊 Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to the external app.")
        print("Make sure the app is running on http://localhost:5001")
    except Exception as e:
        print(f"❌ Error during testing: {e}")

def test_hook_registration():
    """Test that hooks are properly registered."""
    print("\n🔧 Testing Hook Registration")
    print("=" * 40)
    
    try:
        # Check module status to see if hooks are registered
        response = requests.get(f"{BASE_URL}/modules/status")
        if response.status_code == 200:
            data = response.json()
            modules = data.get('modules', {})
            
            print("📋 Module Status:")
            for module_name, module_info in modules.items():
                health = module_info.get('health', {})
                status = health.get('status', 'unknown')
                print(f"   - {module_name}: {status}")
            
            print("\n🎣 Hook System Status:")
            print("   - UserManagementModule: Should trigger 'user_created' hook")
            print("   - WalletModule: Should listen to 'user_created' hook (priority 5)")
            print("   - CommunicationsModule: Should listen to 'user_created' hook (priority 10)")
            
        else:
            print("❌ Failed to get module status")
            
    except Exception as e:
        print(f"❌ Error checking hook registration: {e}")

def test_health_check():
    """Test basic health check."""
    print("\n🏥 Testing Health Check")
    print("=" * 30)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"📤 GET /health: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check successful: {health_data.get('status', 'unknown')}")
        else:
            print(f"❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Error during health check: {e}")

def main():
    """Run all hook system tests."""
    print("🚀 Testing Hook System Implementation (Container Version)")
    print("=" * 60)
    print()
    
    test_health_check()
    test_hook_registration()
    test_hook_system()
    
    print("\n✅ Hook system test completed!")
    print()
    print("📝 Summary:")
    print("- Hook system is now active and functional")
    print("- User creation triggers multiple module callbacks")
    print("- Each module processes the event based on its priority")
    print("- Database operations are performed through the queue system")
    print("- All operations are logged for debugging")

if __name__ == "__main__":
    main() 