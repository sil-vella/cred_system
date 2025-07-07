# User Authentication System

## 🔐 **Overview**

The credit system provides a comprehensive user authentication system that supports multiple authentication methods and integration patterns. Users can register and authenticate either directly through the credit system or through external applications that integrate with the system.

## 🏗️ **Authentication Architecture**

### **Dual Authentication Methods:**

1. **Direct User Authentication** - Users register/login directly with the credit system
2. **External App Authentication** - Users register/login through external applications

### **Authentication Tokens:**

1. **JWT Tokens** - For direct user access and session management
2. **API Keys** - For external application authentication

## 👤 **User Registration Flows**

### **1. Direct User Registration**

**Flow:** User → Credit System Frontend → Credit System Backend

**Process:**
1. User accesses credit system frontend
2. User fills registration form
3. Frontend sends registration request to credit system backend
4. Credit system validates user data and creates account
5. Credit system generates JWT token
6. Frontend receives JWT token and stores it

**Example Request:**
```http
POST /api/users/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "user_id": "user_123",
    "username": "john_doe",
    "email": "john@example.com",
    "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_at": "2024-12-31T23:59:59Z"
  }
}
```

### **2. External App User Registration**

**Flow:** User → External App Frontend → External App Backend → Credit System Backend

**Process:**
1. User accesses external app frontend
2. User fills registration form in external app
3. External app frontend sends data to external app backend
4. External app backend includes API key and forwards to credit system
5. Credit system validates API key and creates user account
6. Credit system generates JWT token and returns to external app
7. External app forwards JWT token to frontend

**Example Request (External App → Credit System):**
```http
POST /api/users/register
X-API-Key: ak_abc123def456...
Content-Type: application/json

{
  "username": "jane_smith",
  "email": "jane@externalapp.com",
  "password": "secure_password",
  "first_name": "Jane",
  "last_name": "Smith",
  "app_id": "external_app_001"
}
```

## 🔑 **User Login Flows**

### **1. Direct User Login**

**Flow:** User → Credit System Frontend → Credit System Backend

**Process:**
1. User enters credentials in credit system frontend
2. Frontend sends login request to credit system backend
3. Credit system validates credentials
4. Credit system generates new JWT token
5. Frontend receives JWT token and stores it

**Example Request:**
```http
POST /api/users/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user_id": "user_123",
    "username": "john_doe",
    "email": "john@example.com",
    "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_at": "2024-12-31T23:59:59Z"
  }
}
```

### **2. External App User Login**

**Flow:** User → External App Frontend → External App Backend → Credit System Backend

**Process:**
1. User enters credentials in external app frontend
2. External app frontend sends data to external app backend
3. External app backend includes API key and forwards to credit system
4. Credit system validates API key and user credentials
5. Credit system generates JWT token and returns to external app
6. External app forwards JWT token to frontend

**Example Request (External App → Credit System):**
```http
POST /api/users/login
X-API-Key: ak_abc123def456...
Content-Type: application/json

{
  "username": "jane_smith",
  "password": "secure_password",
  "app_id": "external_app_001"
}
```

## 🛡️ **Authentication Middleware**

### **Request Processing Flow:**

```
Incoming Request
       ↓
Check for API Key Header
       ↓
If API Key exists:
  - Validate API key
  - Set request.api_key_data
  - Continue to endpoint
       ↓
If no API Key:
  - Check for JWT token
  - Validate JWT token
  - Set request.user_data
  - Continue to endpoint
       ↓
If neither exists:
  - Return 401 Unauthorized
```

### **Authentication Headers:**

**API Key Authentication:**
```http
X-API-Key: ak_abc123def456...
```

**JWT Token Authentication:**
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## 🔄 **Session Management**

### **JWT Token Features:**

1. **Secure Generation**: HMAC-SHA256 with secret key
2. **Configurable Expiration**: Default 24 hours
3. **User Context**: Contains user ID, permissions, app context
4. **Stateless**: No server-side session storage required

### **Token Refresh:**

**Endpoint:** `POST /api/users/refresh-token`

**Request:**
```http
POST /api/users/refresh-token
Authorization: Bearer <EXPIRED_JWT_TOKEN>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "expires_at": "2024-12-31T23:59:59Z"
  }
}
```

## 🚫 **Error Handling**

### **Common Authentication Errors:**

**401 Unauthorized:**
```json
{
  "success": false,
  "error": "authentication_failed",
  "message": "Invalid credentials or missing authentication"
}
```

**403 Forbidden:**
```json
{
  "success": false,
  "error": "insufficient_permissions",
  "message": "User does not have required permissions"
}
```

**422 Validation Error:**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Invalid input data",
  "details": {
    "username": ["Username is required"],
    "email": ["Invalid email format"]
  }
}
```

## 🔧 **User Management Endpoints**

### **User Registration:**
- `POST /api/users/register` - Register new user

### **User Authentication:**
- `POST /api/users/login` - User login
- `POST /api/users/logout` - User logout
- `POST /api/users/refresh-token` - Refresh JWT token

### **User Profile:**
- `GET /api/users/profile` - Get user profile (requires auth)
- `PUT /api/users/profile` - Update user profile (requires auth)
- `PUT /api/users/password` - Change password (requires auth)

### **Password Management:**
- `POST /api/users/forgot-password` - Request password reset
- `POST /api/users/reset-password` - Reset password with token

## 📊 **Security Features**

### **Password Security:**
- **Bcrypt Hashing**: Secure password hashing with salt
- **Minimum Requirements**: Configurable password strength
- **Rate Limiting**: Protection against brute force attacks

### **JWT Security:**
- **Secret Key**: Environment-based secret key
- **Expiration**: Configurable token expiration
- **Blacklisting**: Support for token revocation

### **API Key Security:**
- **HMAC Generation**: Secure API key generation
- **Permission-Based**: Granular permission control
- **Expiration**: Automatic API key expiration

## 🚀 **Integration Examples**

### **Direct User Integration:**
```python
import requests

# User registration
def register_user(user_data):
    response = requests.post(
        "http://localhost:8080/api/users/register",
        json=user_data
    )
    return response.json()

# User login
def login_user(credentials):
    response = requests.post(
        "http://localhost:8080/api/users/login",
        json=credentials
    )
    return response.json()

# Authenticated request
def get_user_profile(jwt_token):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.get(
        "http://localhost:8080/api/users/profile",
        headers=headers
    )
    return response.json()
```

### **External App Integration:**
```python
import requests

# External app configuration
CREDIT_SYSTEM_URL = "http://credit-system:5001"
API_KEY = "ak_abc123def456..."

# Register user through external app
def register_user_external(user_data):
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

# Login user through external app
def login_user_external(credentials):
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{CREDIT_SYSTEM_URL}/api/users/login",
        json=credentials,
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        return result["data"]["jwt_token"]
    else:
        raise Exception("Login failed")
```

## 📈 **Monitoring and Analytics**

### **Authentication Metrics:**
- **Registration Rate**: New user registrations per time period
- **Login Success Rate**: Successful vs failed login attempts
- **Token Usage**: JWT token generation and validation counts
- **API Key Usage**: External app authentication patterns

### **Security Monitoring:**
- **Failed Login Attempts**: Track potential security threats
- **Rate Limit Violations**: Monitor for abuse patterns
- **Token Expiration**: Track token lifecycle
- **API Key Activity**: Monitor external app usage

This comprehensive authentication system provides secure, scalable user management for both direct users and external application integrations. 