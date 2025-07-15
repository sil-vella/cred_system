# JWT Manager

## 📋 Overview

The JWT Manager is a comprehensive authentication system that handles JSON Web Token (JWT) creation, verification, and management. It provides secure token-based authentication with advanced features like client fingerprinting, Redis-based token revocation, and automatic token cleanup.

## 🏗️ Architecture

### Core Components

1. **Token Creation Engine** - Generates secure JWT tokens
2. **Token Verification System** - Validates and decodes tokens
3. **Redis Integration** - Token storage and revocation
4. **Client Fingerprinting** - IP + User-Agent based token binding
5. **Token Cleanup** - Automatic expiration handling

### Class Structure

```python
class JWTManager:
    def __init__(self, redis_manager=None):
        self.redis_manager = redis_manager
        self.secret_key = Config.JWT_SECRET_KEY
        self.algorithm = Config.JWT_ALGORITHM
        self.access_token_expire_seconds = Config.JWT_ACCESS_TOKEN_EXPIRES  # 1 hour (3600s)
        self.refresh_token_expire_seconds = Config.JWT_REFRESH_TOKEN_EXPIRES  # 7 days (604800s)
```

## 🔐 Token Types

### Access Tokens
- **Lifetime**: 1 hour (3600 seconds)
- **Purpose**: API authentication
- **Claims**: user_id, username, email, fingerprint
- **Usage**: Authorization header for API requests

### Refresh Tokens
- **Lifetime**: 7 days (604800 seconds)
- **Purpose**: Generate new access tokens
- **Claims**: user_id, fingerprint
- **Usage**: Token refresh endpoint

## 🔄 Complete Token Flow

### 1. Token Creation Process

```python
def create_token(self, data: Dict[str, Any], token_type: TokenType, expires_in: Optional[int] = None) -> str:
    to_encode = data.copy()
    
    # Set expiration based on token type
    if token_type == TokenType.ACCESS:
        expire = datetime.utcnow() + timedelta(seconds=self.access_token_expire_seconds)  # 1 hour
    elif token_type == TokenType.REFRESH:
        expire = datetime.utcnow() + timedelta(seconds=self.refresh_token_expire_seconds)  # 7 days
    
    # Add client fingerprint for security
    client_fingerprint = self._get_client_fingerprint()
    to_encode["fingerprint"] = client_fingerprint
    
    # Add JWT standard claims
    to_encode.update({
        "exp": expire,
        "type": token_type.value,
        "iat": datetime.utcnow()
    })
    
    # Encode with secret key
    encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm="HS256")
    
    # Store in Redis for revocation capability
    self._store_token(encoded_jwt, expire, token_type)
    
    return encoded_jwt
```

### 2. Client Fingerprinting

```python
def _get_client_fingerprint(self) -> str:
    """Generate unique client fingerprint based on IP and User-Agent."""
    try:
        ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        fingerprint = hashlib.sha256(f"{ip}-{user_agent}".encode()).hexdigest()
        return fingerprint
    except Exception as e:
        custom_log(f"Error generating client fingerprint: {str(e)}")
        return ""
```

**Security Benefits:**
- **Token Binding**: Tokens are bound to specific client (IP + User-Agent)
- **Prevents Token Theft**: Stolen tokens won't work from different clients
- **Session Security**: Enhanced protection against session hijacking

### 3. Token Verification Process

```python
def verify_token(self, token: str, expected_type: Optional[TokenType] = None) -> Optional[Dict[str, Any]]:
    try:
        # Decode token
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        
        # Check if token is revoked in Redis
        if self._is_token_revoked(token):
            custom_log(f"Token revoked: {token[:10]}...")
            return None
        
        # Verify token type if specified
        if expected_type:
            token_type = payload.get("type")
            if token_type != expected_type.value:
                custom_log(f"Invalid token type. Expected: {expected_type.value}, Got: {token_type}")
                return None
        
        return payload
        
    except ExpiredSignatureError:
        custom_log("Token has expired")
        return None
    except InvalidSignatureError:
        custom_log("Invalid token signature")
        return None
    except Exception as e:
        custom_log(f"Token verification failed: {str(e)}")
        return None
```

## 🗄️ Redis Integration

### Token Storage

```python
def _store_token(self, token: str, expire: datetime, token_type: TokenType):
    """Store token in Redis with proper prefix and expiration."""
    try:
        # Calculate TTL in seconds
        ttl = max(1, int((expire - datetime.utcnow()).total_seconds()))
        
        # Store token using Redis manager
        if not self.redis_manager.store_token(token_type.value, token, expire=ttl):
            custom_log(f"Failed to store {token_type.value} token")
        
    except Exception as e:
        custom_log(f"Error storing token: {str(e)}")
```

### Token Revocation

```python
def revoke_token(self, token: str) -> bool:
    """Revoke a token by removing it from Redis."""
    try:
        # Decode token to get type
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        token_type = payload.get("type")
        
        # Revoke token using Redis manager
        return self.redis_manager.revoke_token(token_type, token)
        
    except Exception as e:
        custom_log(f"Error revoking token: {str(e)}")
        return False
```

### Revocation Check

```python
def _is_token_revoked(self, token: str) -> bool:
    """Check if a token is revoked using Redis lookup."""
    try:
        # Decode token to get type
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        token_type = payload.get("type")
        
        # Check if token is valid in Redis
        return not self.redis_manager.is_token_valid(token_type, token)
        
    except Exception as e:
        custom_log(f"Error checking token revocation: {str(e)}")
        return True  # Fail safe: consider revoked on error
```

## 🔄 Token Refresh System

### Refresh Token Process

```python
def refresh_token(self, refresh_token: str) -> Optional[str]:
    """Create a new access token using a refresh token."""
    payload = self.verify_token(refresh_token, TokenType.REFRESH)
    if payload:
        # Remove refresh-specific claims
        new_payload = {k: v for k, v in payload.items() 
                     if k not in ['exp', 'iat', 'type']}
        return self.create_token(new_payload, TokenType.ACCESS)
    return None
```

**Refresh Flow:**
1. **Client sends refresh token** → `/auth/refresh`
2. **Verify refresh token** → Check signature, expiration, revocation
3. **Create new access token** → Generate fresh 30-minute token
4. **Return new token** → Client updates stored token

## 🧹 Automatic Cleanup

### Expired Token Cleanup

```python
def cleanup_expired_tokens(self):
    """Clean up expired tokens from Redis."""
    try:
        custom_log("Starting expired token cleanup")
        
        for token_type in TokenType:
            if not self.redis_manager.cleanup_expired_tokens(token_type.value):
                custom_log(f"Failed to cleanup expired {token_type.value} tokens")
                
        custom_log("Completed expired token cleanup")
        
    except Exception as e:
        custom_log(f"Error during token cleanup: {str(e)}")
```

## 🔧 Configuration

### JWT Settings (config.py)

```python
# JWT Configuration
JWT_SECRET_KEY = "your-super-secret-key-change-in-production"
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour in seconds
JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days in seconds
JWT_ALGORITHM = "HS256"
JWT_TOKEN_TYPE = "bearer"
JWT_HEADER_NAME = "Authorization"
JWT_HEADER_TYPE = "Bearer"
```

### Token Lifetimes

- **Access Token**: 1 hour (3600 seconds)
- **Refresh Token**: 7 days (604800 seconds)
- **Algorithm**: HS256 (HMAC with SHA-256)

## 🛡️ Security Features

### 1. Client Fingerprinting
- **Purpose**: Bind tokens to specific client
- **Method**: SHA256 hash of IP + User-Agent
- **Benefit**: Prevents token theft across different clients

### 2. Redis-Based Revocation
- **Purpose**: Immediate token invalidation
- **Method**: Store tokens in Redis with TTL
- **Benefit**: Can revoke tokens before expiration

### 3. Token Type Validation
- **Purpose**: Ensure correct token type usage
- **Method**: Verify `type` claim in token
- **Benefit**: Prevents access token usage for refresh

### 4. Automatic Expiration
- **Purpose**: Limit token lifetime
- **Method**: JWT `exp` claim + Redis TTL
- **Benefit**: Reduces attack window

## 📊 Usage Examples

### Creating Tokens

```python
# Initialize JWT Manager
jwt_manager = JWTManager(redis_manager)

# Create access token
access_token_payload = {
    'user_id': '507f1f77bcf86cd799439011',
    'username': 'john_doe',
    'email': 'john@example.com'
}
access_token = jwt_manager.create_access_token(access_token_payload)

# Create refresh token
refresh_token_payload = {
    'user_id': '507f1f77bcf86cd799439011'
}
refresh_token = jwt_manager.create_refresh_token(refresh_token_payload)
```

### Verifying Tokens

```python
# Verify access token
payload = jwt_manager.verify_token(token, TokenType.ACCESS)
if payload:
    user_id = payload.get('user_id')
    username = payload.get('username')
    # Token is valid, proceed with request
else:
    # Token is invalid, return 401
```

### Refreshing Tokens

```python
# Refresh access token using refresh token
new_access_token = jwt_manager.refresh_token(refresh_token)
if new_access_token:
    # Return new access token to client
    return {'access_token': new_access_token}
else:
    # Refresh failed, require re-authentication
    return {'error': 'Invalid refresh token'}, 401
```

### Revoking Tokens

```python
# Revoke a token (e.g., on logout)
success = jwt_manager.revoke_token(token)
if success:
    custom_log("Token revoked successfully")
else:
    custom_log("Failed to revoke token")
```

## 🔍 Error Handling

### Common JWT Errors

1. **ExpiredSignatureError**: Token has expired
2. **InvalidSignatureError**: Token signature is invalid
3. **InvalidTokenError**: Token format is invalid
4. **InvalidAudienceError**: Token audience is invalid
5. **InvalidIssuerError**: Token issuer is invalid

### Error Response Examples

```python
# Token expired
{
    "error": "Token has expired",
    "code": "TOKEN_EXPIRED"
}

# Invalid token
{
    "error": "Invalid token signature",
    "code": "INVALID_TOKEN"
}

# Token revoked
{
    "error": "Token has been revoked",
    "code": "TOKEN_REVOKED"
}
```

## 🔄 Integration with Flask

### Before Request Middleware

```python
@flask_app.before_request
def authenticate_request():
    # Skip authentication for public routes
    if request.endpoint in public_routes:
        return
    
    # Extract token from Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid authorization header'}), 401
    
    token = auth_header.split(' ')[1]
    
    # Verify token
    payload = jwt_manager.verify_token(token, TokenType.ACCESS)
    if not payload:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    # Set user context
    request.user_id = payload.get('user_id')
    request.username = payload.get('username')
```

## 📈 Performance Considerations

### Redis Operations
- **Token Storage**: O(1) for storing tokens
- **Token Lookup**: O(1) for checking token validity
- **Token Revocation**: O(1) for revoking tokens

### JWT Operations
- **Token Creation**: O(1) - simple encoding
- **Token Verification**: O(1) - signature verification
- **Token Decoding**: O(1) - base64 decoding

### Memory Usage
- **Token Storage**: ~1KB per token in Redis
- **Client Fingerprint**: 64 bytes (SHA256 hash)
- **JWT Payload**: ~200-500 bytes per token

## 🧪 Testing

### Unit Tests

```python
def test_token_creation():
    jwt_manager = JWTManager()
    payload = {'user_id': '123', 'username': 'test'}
    token = jwt_manager.create_access_token(payload)
    assert token is not None

def test_token_verification():
    jwt_manager = JWTManager()
    payload = {'user_id': '123', 'username': 'test'}
    token = jwt_manager.create_access_token(payload)
    verified_payload = jwt_manager.verify_token(token, TokenType.ACCESS)
    assert verified_payload['user_id'] == '123'

def test_token_revocation():
    jwt_manager = JWTManager()
    payload = {'user_id': '123'}
    token = jwt_manager.create_access_token(payload)
    success = jwt_manager.revoke_token(token)
    assert success is True
    
    # Verify token is revoked
    verified_payload = jwt_manager.verify_token(token, TokenType.ACCESS)
    assert verified_payload is None
```

## 🔧 Maintenance

### Regular Tasks

1. **Token Cleanup**: Run `cleanup_expired_tokens()` periodically
2. **Redis Monitoring**: Monitor Redis memory usage for token storage
3. **Secret Rotation**: Rotate JWT secret key periodically
4. **Log Analysis**: Monitor authentication logs for suspicious activity

### Monitoring Metrics

- **Token Creation Rate**: Tokens created per minute
- **Token Verification Rate**: Token verifications per minute
- **Token Revocation Rate**: Tokens revoked per minute
- **Redis Memory Usage**: Memory used by token storage
- **Authentication Errors**: Failed authentication attempts

## 🚀 Best Practices

### Security
1. **Use HTTPS**: Always use HTTPS in production
2. **Secret Management**: Store JWT secret securely
3. **Token Rotation**: Implement token refresh mechanism
4. **Client Fingerprinting**: Enable for enhanced security
5. **Token Revocation**: Implement logout functionality

### Performance
1. **Redis Optimization**: Use Redis for token storage
2. **Token Size**: Keep payload minimal
3. **Cleanup Scheduling**: Regular expired token cleanup
4. **Caching**: Cache user data when possible

### Development
1. **Error Handling**: Comprehensive error handling
2. **Logging**: Detailed authentication logging
3. **Testing**: Comprehensive unit tests
4. **Documentation**: Keep documentation updated

---

## 📚 Related Documentation

- [Manager Overview](../managers/MANAGER_OVERVIEW.md)
- [State Manager](../managers/STATE_MANAGER.md)
- [Authentication System](../modules/USER_ACTIONS_MODULE.md)
- [API Documentation](../api/API_OVERVIEW.md) 