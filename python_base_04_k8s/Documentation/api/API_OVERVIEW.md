# API Documentation Overview

## 🌐 Introduction

The Flask Credit System provides a comprehensive REST API for credit management operations. The API follows RESTful principles and is organized around the module-first architecture.

## 🏗️ API Architecture

### **Module-Based Endpoints**
Each module exposes its own set of endpoints:

```
/health                     # System health
/modules/*                  # Module management
/wallet/*                   # Wallet operations
/transactions/*             # Transaction operations  
/users/*                    # User management
/auth/*                     # Authentication
```

### **Response Format**
All API responses follow a consistent format:

```json
{
    "success": true,
    "data": {
        // Response data
    },
    "message": "Operation completed successfully",
    "timestamp": "2024-07-01T18:30:00Z"
}
```

Error responses:
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input data",
        "details": {}
    },
    "timestamp": "2024-07-01T18:30:00Z"
}
```

## 🔐 Authentication

### **JWT Token Authentication**
Most endpoints require JWT authentication:

```bash
Authorization: Bearer <jwt_token>
```

### **Token Acquisition**
```bash
POST /auth/login
Content-Type: application/json

{
    "username": "user@example.com",
    "password": "secure_password"
}
```

Response:
```json
{
    "success": true,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "Bearer",
        "expires_in": 3600,
        "user_id": "user_123"
    }
}
```

## 🏆 Core API Endpoints

### **System Health**
```bash
GET /health
```
Returns overall system health including modules and managers.

### **Module Management**
```bash
GET /modules/status                    # All module status
GET /modules/{module_name}/health      # Specific module health
```

### **Wallet Operations**
```bash
GET /wallet/info                       # Wallet module information
GET /wallet/balance/{user_id}          # Get user balance
POST /wallet/deposit                   # Deposit credits
POST /wallet/withdraw                  # Withdraw credits
```

### **Transaction Operations**
```bash
GET /transactions/info                 # Transaction module info
GET /transactions/{user_id}            # User transaction history
POST /transactions/transfer            # Transfer between users
```

### **User Management**
```bash
GET /users/{user_id}                   # Get user details
POST /users                            # Create new user
PUT /users/{user_id}                   # Update user
DELETE /users/{user_id}                # Delete user
```

## 📊 Request/Response Examples

### **Create User**
```bash
POST /users
Authorization: Bearer <token>
Content-Type: application/json

{
    "username": "newuser",
    "email": "newuser@example.com",
    "full_name": "New User",
    "initial_balance": 100.00
}
```

Response:
```json
{
    "success": true,
    "data": {
        "user_id": "user_456",
        "username": "newuser",
        "email": "newuser@example.com",
        "full_name": "New User",
        "balance": 100.00,
        "created_at": "2024-07-01T18:30:00Z"
    }
}
```

### **Transfer Credits**
```bash
POST /transactions/transfer
Authorization: Bearer <token>
Content-Type: application/json

{
    "from_user_id": "user_123",
    "to_user_id": "user_456", 
    "amount": 50.00,
    "description": "Payment for services"
}
```

Response:
```json
{
    "success": true,
    "data": {
        "transaction_id": "txn_789",
        "from_user_id": "user_123",
        "to_user_id": "user_456",
        "amount": 50.00,
        "status": "completed",
        "timestamp": "2024-07-01T18:30:00Z"
    }
}
```

## ⚡ Rate Limiting

### **Rate Limit Headers**
All responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1625151600
```

### **Rate Limit Exceeded**
```json
{
    "success": false,
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Rate limit exceeded. Try again later.",
        "retry_after": 60
    }
}
```

## 🔍 Error Handling

### **Standard Error Codes**
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error (system error)

### **Error Response Structure**
```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable error message",
        "details": {
            "field": "Additional error details"
        }
    },
    "timestamp": "2024-07-01T18:30:00Z"
}
```

## 📝 Request Validation

### **Input Validation**
All endpoints validate input data:

```json
// Invalid request
{
    "username": "",  // Required field empty
    "email": "invalid-email"  // Invalid format
}

// Error response
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Input validation failed",
        "details": {
            "username": "Username is required",
            "email": "Invalid email format"
        }
    }
}
```

## 🔒 Security Features

### **Field-Level Encryption**
Sensitive data is automatically encrypted:
- Email addresses
- Personal information
- Financial data

### **CORS Configuration**
Cross-origin requests are properly configured:
```
Access-Control-Allow-Origin: https://yourdomain.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Authorization, Content-Type
```

### **Request Sanitization**
All input is sanitized to prevent:
- SQL injection attacks
- XSS vulnerabilities
- Command injection

## 📊 API Monitoring

### **Metrics Collection**
All API calls are monitored:
- Request/response times
- Error rates
- Endpoint usage statistics
- User activity patterns

### **Health Monitoring**
Regular health checks ensure API availability:
```bash
GET /health
```

## 🚀 API Versioning

### **Current Version**
- **Version**: v1.0
- **Base URL**: `http://localhost:5000`
- **Documentation**: This document

### **Future Versioning**
Future API versions will be supported via:
- URL versioning: `/v2/users`
- Header versioning: `Accept: application/vnd.api+json;version=2`

## 📱 SDK & Client Libraries

### **HTTP Client Examples**

#### **cURL**
```bash
# Get user balance
curl -X GET \
  'http://localhost:5000/wallet/balance/user_123' \
  -H 'Authorization: Bearer <token>'
```

#### **Python**
```python
import requests

headers = {'Authorization': 'Bearer <token>'}
response = requests.get(
    'http://localhost:5000/wallet/balance/user_123',
    headers=headers
)
data = response.json()
```

#### **JavaScript**
```javascript
const response = await fetch('/wallet/balance/user_123', {
    headers: {
        'Authorization': 'Bearer <token>',
        'Content-Type': 'application/json'
    }
});
const data = await response.json();
```

## 🧪 Testing the API

### **Health Check**
```bash
curl http://localhost:5000/health
```

### **Module Status**
```bash
curl http://localhost:5000/modules/status
```

### **Authentication Test**
```bash
# Login
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'

# Use token
curl -X GET http://localhost:5000/wallet/info \
  -H "Authorization: Bearer <token>"
```

## 📚 Additional Resources

### **Detailed Documentation**
- [Authentication Endpoints](AUTHENTICATION.md)
- [User Management API](USER_ENDPOINTS.md)
- [Wallet Operations API](WALLET_ENDPOINTS.md)
- [Transaction Management API](TRANSACTION_ENDPOINTS.md)
- [System Health API](SYSTEM_ENDPOINTS.md)

### **Development Resources**
- [API Testing Guide](../development/TESTING_GUIDE.md)
- [Module Development](../development/MODULE_DEVELOPMENT.md)
- [Error Handling](../development/DEBUGGING_GUIDE.md)

---

*The Flask Credit System API provides a robust, secure, and well-documented interface for all credit management operations. Follow the linked guides for detailed endpoint documentation and usage examples.* 