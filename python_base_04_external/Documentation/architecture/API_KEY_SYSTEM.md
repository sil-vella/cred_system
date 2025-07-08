# API Key System Architecture

## 🔑 **Overview**

The credit system implements a **dual authentication system** that supports both **JWT tokens** (for direct user access) and **API keys** (for external application integration). This allows external apps to securely interact with the credit system while maintaining proper access control.

## 🏗️ **Architecture Components**

### 1. **API Key Manager** (`api_key_manager.py`)
- **Purpose**: Core service for generating, validating, and managing API keys
- **Storage**: Redis-based with 30-day expiration
- **Security**: HMAC-SHA256 generation using encryption key

### 2. **Authentication Middleware** (`app_manager.py`)
- **Purpose**: Intercepts all incoming requests
- **Logic**: 
  - Checks for API key in `X-API-Key` header
  - If API key exists, validates it and sets `request.api_key_data`
  - If no API key, falls back to JWT token validation
  - If neither exists, returns 401 Unauthorized

### 3. **Connection API Module** (`communications_main.py`)
- **Purpose**: Provides API key management endpoints
- **Endpoints**:
  - `POST /api-keys/generate` - Generate new API key
  - `GET /api-keys/validate` - Validate existing API key
  - `GET /api-keys/list` - List all API keys (requires auth)
  - `DELETE /api-keys/revoke` - Revoke API key (requires auth)

## 🔄 **Complete User Registration Flow for External Apps**

### **Step-by-Step Process:**

1. **Frontend App** → **App Backend**
   - User fills registration form in external app's frontend
   - Frontend sends user details to its own backend API

2. **App Backend** → **Credit System Backend**
   - App backend receives user registration request
   - App backend includes its **API key** in the request header
   - App backend forwards user details + API key to credit system

3. **Credit System Backend** → **Processing**
   - Credit system validates the API key
   - Credit system creates the user account
   - Credit system generates a **JWT token** for the new user
   - Credit system returns success response + JWT token

4. **Credit System Backend** → **App Backend** → **Frontend**
   - App backend receives success response + JWT token
   - App backend forwards JWT token to frontend
   - Frontend stores JWT token for future authenticated requests

## 🔐 **Security Flow:**

```
External App Frontend
         ↓
   App Backend (with API Key)
         ↓
   Credit System Backend
         ↓
   User Created + JWT Generated
         ↓
   App Backend (receives JWT)
         ↓
   Frontend (stores JWT)
```

## 📋 **Example Request Flow:**

### **1. App Backend → Credit System:**
```http
POST /api/users/register
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password",
  "app_id": "external_app_001"
}
```

### **2. Credit System Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "user_id": "user_123",
    "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_at": "2024-12-31T23:59:59Z"
  }
}
```

## 🎯 **Key Benefits:**

1. **Centralized User Management**: All users are created in the credit system
2. **API Key Security**: External apps authenticate via API keys
3. **JWT Token Flow**: Users get JWT tokens for direct API access
4. **Separation of Concerns**: External apps handle their own UI/UX, credit system handles user management
5. **Scalable Architecture**: Multiple external apps can integrate using the same pattern

## 🔧 **API Key Management Endpoints**

### **Generate API Key**
```http
POST /api-keys/generate
Content-Type: application/json

{
  "app_id": "external_app_001",
  "app_name": "External Application",
  "permissions": ["read", "write"]
}
```

**Response:**
```json
{
  "success": true,
  "api_key": "ak_abc123def456...",
  "app_id": "external_app_001",
  "permissions": ["read", "write"],
  "expires_at": "2024-12-31T23:59:59Z"
}
```

### **Validate API Key**
```http
GET /api-keys/validate
X-API-Key: ak_abc123def456...
```

**Response:**
```json
{
  "valid": true,
  "app_id": "external_app_001",
  "permissions": ["read", "write"],
  "expires_at": "2024-12-31T23:59:59Z"
}
```

### **List API Keys** (requires authentication)
```http
GET /api-keys/list
Authorization: Bearer <JWT_TOKEN>
```

### **Revoke API Key** (requires authentication)
```http
DELETE /api-keys/revoke
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "api_key": "ak_abc123def456..."
}
```

## 🛡️ **Security Features**

### **API Key Security:**
- **HMAC-SHA256 Generation**: Uses encryption key for secure generation
- **30-Day Expiration**: Automatic expiration for security
- **Redis Storage**: Fast, distributed storage with TTL
- **Permission-Based Access**: Granular permission control

### **Authentication Flow:**
- **Dual Authentication**: Supports both API keys and JWT tokens
- **Fallback Mechanism**: API key → JWT token → Unauthorized
- **Request Context**: API key data available in request object
- **Rate Limiting**: Configurable rate limiting per IP/API key

## 🚀 **Integration Example**

### **External App Setup:**
```python
# External app backend configuration
CREDIT_SYSTEM_URL = "http://credit-system:5001"
API_KEY = "ak_abc123def456..."

# User registration request
def register_user(user_data):
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{CREDIT_SYSTEM_URL}/api/users/register",
        json=user_data,
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        return result["data"]["jwt_token"]
    else:
        raise Exception("Registration failed")
```

## 📊 **Monitoring and Logging**

### **API Key Usage Tracking:**
- All API key validations are logged
- Failed authentication attempts are tracked
- Rate limiting violations are monitored
- API key generation/revocation events are logged

### **Health Checks:**
- API key service health monitoring
- Redis connectivity checks
- Rate limiting status monitoring
- Authentication service status

This architecture allows external apps to seamlessly integrate with the credit system while maintaining proper security and user management standards. 