# CSUserManagementModule Documentation

## Overview

The **CSUserManagementModule** is a comprehensive user management system that handles user authentication, registration, profile management, and session control. It provides a complete set of RESTful API endpoints for user operations while utilizing the queue-based database system for optimal performance and consistency.

## 🎯 Purpose

- **User Authentication**: Login, logout, and token management
- **User Registration**: Account creation with validation
- **Profile Management**: CRUD operations for user profiles
- **Session Control**: JWT token-based authentication
- **Database Integration**: Queue-based operations for consistency

## 📋 Dependencies

```python
dependencies = ["communications_module"]
```

The module depends on the CommunicationsModule for infrastructure services like database connections and JWT management.

## 🏗️ Architecture

### Core Components

1. **Database Managers**
   - `self.db_manager`: Queue-based write operations
   - `self.analytics_db`: Read-only operations
   - `self.redis_manager`: Caching and session management

2. **JWT Management**
   - Token creation and validation
   - Access and refresh token handling
   - Token revocation

3. **Queue System Integration**
   - All database operations go through the queue
   - Ensures data consistency
   - Provides audit trail capabilities

## 🔧 API Endpoints

### User CRUD Operations

#### 1. Create User
```http
POST /users
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "password123"
}
```

**Response:**
```json
{
  "message": "User created successfully",
  "user": {
    "_id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "username": "username",
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "status": "created"
}
```

#### 2. Get User
```http
GET /users/{user_id}
```

**Response:**
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "username",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### 3. Update User
```http
PUT /auth/{user_id}
Content-Type: application/json

{
  "username": "new_username",
  "email": "newemail@example.com",
  "status": "active"
}
```

#### 4. Delete User
```http
DELETE /auth/{user_id}
```

#### 5. Search Users
```http
POST /users/search
Content-Type: application/json

{
  "username": "john",
  "email": "john@",
  "status": "active"
}
```

### Authentication Endpoints

#### 1. User Registration
```http
POST /auth/register
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "securepassword123"
}
```

**Features:**
- Email format validation
- Password strength validation (minimum 8 characters)
- Duplicate email/username checking
- Automatic wallet creation
- Bcrypt password hashing

#### 2. User Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "_id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "username": "username",
      "status": "active"
    },
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 1800
  }
}
```

#### 3. User Logout
```http
POST /auth/logout
Authorization: Bearer {access_token}
```

#### 4. Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 5. Get Current User
```http
GET /auth/me
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "_id": "507f1f77bcf86cd799439011",
      "email": "user@example.com",
      "username": "username",
      "status": "active"
    },
    "wallet": {
      "_id": "507f1f77bcf86cd799439021",
      "user_id": "507f1f77bcf86cd799439011",
      "balance": 1500,
      "currency": "credits"
    }
  }
}
```

## 🔐 Security Features

### Password Security
- **Bcrypt Hashing**: All passwords are hashed using bcrypt
- **Salt Generation**: Automatic salt generation for each password
- **Strength Validation**: Minimum 8 characters required

### Token Security
- **JWT Tokens**: Access and refresh token system
- **Token Expiration**: Configurable token lifetimes
- **Token Revocation**: Secure logout with token invalidation
- **Bearer Authentication**: Standard HTTP Authorization header

### Input Validation
- **Email Validation**: RFC-compliant email format checking
- **Username Validation**: Alphanumeric and length validation
- **SQL Injection Prevention**: Parameterized queries
- **XSS Prevention**: Input sanitization

## 📊 Database Integration

### Queue System Usage
The module uses the queue-based database system for all operations:

```python
# Write operations (queue system)
user_id = self.db_manager.insert("users", user_data)
modified_count = self.db_manager.update("users", query, update_data)
deleted_count = self.db_manager.delete("users", query)

# Read operations (queue system)
user = self.db_manager.find_one("users", {"email": email})
users = self.db_manager.find("users", query)
```

### Database Collections
- **users**: User profiles and authentication data
- **wallets**: User wallet information
- **user_sessions**: Session management (if implemented)
- **user_tokens**: Token storage (if implemented)

### Indexes Utilized
- `email` (unique): Fast email lookups
- `username`: Username searches
- `status`: User status filtering
- `created_at`: Time-based queries

## 🚀 Performance Optimizations

### 1. Efficient Login Process
**Before (Inefficient):**
```python
# Fetched ALL users from database
all_users = self.db_manager.find("users", {})
for u in all_users:
    if u.get('email') == email:
        user = u
        break
```

**After (Optimized):**
```python
# Direct indexed query
user = self.db_manager.find_one("users", {"email": email})
```

### 2. Queue System Benefits
- **Consistency**: All operations go through the same queue
- **Audit Trail**: Complete operation logging
- **Error Handling**: Centralized error management
- **Scalability**: Handles high concurrent loads

### 3. Caching Strategy
- **Redis Integration**: Session and token caching
- **Query Caching**: Frequently accessed data
- **Invalidation**: Smart cache invalidation on updates

## 🔧 Configuration

### Environment Variables
```bash
# Database Configuration
MONGODB_URI=mongodb://localhost:27017/credit_system
MONGODB_USER=credit_app_user
MONGODB_PASSWORD=6R3jjsvVhIRP20zMiHdkBzNKx

# JWT Configuration
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRES=1800  # 30 minutes
JWT_REFRESH_TOKEN_EXPIRES=604800  # 7 days

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Module Settings
```python
# Session timeout (1 hour)
session_timeout = 3600

# Maximum concurrent sessions per user
max_concurrent_sessions = 1

# Session check interval (5 minutes)
session_check_interval = 300
```

## 📝 Error Handling

### HTTP Status Codes
- **200**: Success
- **201**: Created
- **400**: Bad Request (validation errors)
- **401**: Unauthorized (invalid credentials)
- **404**: Not Found (user not found)
- **409**: Conflict (duplicate email/username)
- **500**: Internal Server Error

### Error Response Format
```json
{
  "success": false,
  "error": "Error message description"
}
```

## 🧪 Testing

### Test Endpoint
```http
GET /auth/test
```

Returns debug information about the module's database connections and configuration.

### Health Check
```python
def health_check(self) -> Dict[str, Any]:
    """Perform health check for CSUserManagementModule."""
    health_status = super().health_check()
    health_status['dependencies'] = self.dependencies
    
    # Add database queue status
    try:
        queue_status = self.db_manager.get_queue_status()
        health_status['details'] = {
            'database_queue': {
                'queue_size': queue_status['queue_size'],
                'worker_alive': queue_status['worker_alive'],
                'queue_enabled': queue_status['queue_enabled'],
                'pending_results': queue_status['pending_results']
            }
        }
    except Exception as e:
        health_status['details'] = {'database_queue': f'error: {str(e)}'}
    
    return health_status
```

## 🔄 Integration with Other Modules

### CommunicationsModule Dependency
The module depends on CommunicationsModule for:
- Database connection management
- JWT token handling
- Redis caching services
- Error handling utilities

### Wallet Integration
- Automatic wallet creation on user registration
- Wallet balance retrieval in user profile
- Wallet status tracking

### Audit Trail
- All user operations are logged
- Login attempts tracked
- Profile changes recorded
- Token operations monitored

## 📈 Monitoring and Logging

### Custom Logging
```python
custom_log(f"✅ User logged in successfully: {user['username']} ({email})")
custom_log(f"❌ Error during login: {e}")
```

### Debug Information
- Database connection status
- Queue system health
- Token validation results
- User operation tracking

## 🚀 Usage Examples

### 1. User Registration Flow
```python
# 1. Validate input
# 2. Check for duplicates
# 3. Hash password
# 4. Create user via queue
# 5. Create wallet
# 6. Return success response
```

### 2. User Login Flow
```python
# 1. Validate credentials
# 2. Find user by email (indexed query)
# 3. Verify password hash
# 4. Update login statistics
# 5. Generate JWT tokens
# 6. Return tokens and user data
```

### 3. Token Refresh Flow
```python
# 1. Validate refresh token
# 2. Get user data
# 3. Revoke old tokens
# 4. Generate new tokens
# 5. Return new access token
```

## 🔧 Development Guidelines

### Adding New Features
1. **Follow Queue Pattern**: Use `self.db_manager` for all operations
2. **Validate Input**: Implement proper validation for all inputs
3. **Handle Errors**: Use try-catch blocks with proper error responses
4. **Log Operations**: Use `custom_log()` for important events
5. **Update Documentation**: Keep this documentation current

### Code Standards
- **Type Hints**: Use Python type hints for function parameters
- **Docstrings**: Document all public methods
- **Error Messages**: Provide clear, user-friendly error messages
- **Security**: Never expose sensitive information in responses

## 📚 Related Documentation

- [Database Structure Setup](../database/README_10_setup_database_structure.md)
- [CommunicationsModule Documentation](./communications_module.md)
- [Queue System Documentation](../managers/database_manager.md)
- [JWT Manager Documentation](../managers/jwt_manager.md)

---

**Last Updated**: March 2024  
**Version**: 1.0.0  
**Maintainer**: Development Team 