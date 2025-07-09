# New Route Registration System

## Overview

The new route registration system simplifies authentication by automatically determining authentication requirements based on route prefixes. This eliminates the need to hardcode public routes and authentication rules in the middleware.

## 🔄 **How It Works**

### **Route Prefix Rules**

| Prefix | Authentication Required | Description |
|--------|----------------------|-------------|
| `/public/*` | None | Public routes, no authentication required |
| `/userauth/*` | JWT Token | User authentication required |
| `/keyauth/*` | API Key | Application authentication required |
| All others | None | Default to public (no authentication) |

### **Registration Methods**

#### **1. Smart Registration (Recommended)**
```python
def register_routes(self):
    # Automatically determines auth based on route prefix
    self._register_auth_route_helper("/public/users/info", self.get_public_info)
    self._register_auth_route_helper("/userauth/users/profile", self.get_profile)
    self._register_auth_route_helper("/keyauth/users/create", self.create_user)
```

#### **2. Explicit Registration**
```python
def register_routes(self):
    # Explicitly specify authentication type
    self._register_route_helper("/custom/route", self.handler, auth="jwt")
    self._register_route_helper("/another/route", self.handler, auth="key")
    self._register_route_helper("/public/route", self.handler, auth=None)
```

## 📋 **Usage Examples**

### **Public Routes**
> **Note:** Registration and login endpoints (e.g., `/public/register`, `/public/login`) require deterministic encryption for email/username fields to allow secure login and lookup. See [User Authentication System](./architecture/USER_AUTHENTICATION_SYSTEM.md) and [Manager Overview](./managers/MANAGER_OVERVIEW.md).

```python
# No authentication required
self._register_auth_route_helper("/public/health", self.health_check)
self._register_auth_route_helper("/public/info", self.get_info)
self._register_auth_route_helper("/public/status", self.get_status)
```

### **JWT Protected Routes**
> **Note:** JWT-protected login endpoints also use deterministic encryption for searchable fields.

```python
# Requires valid JWT token
self._register_auth_route_helper("/userauth/profile", self.get_profile)
self._register_auth_route_helper("/userauth/settings", self.get_settings)
self._register_auth_route_helper("/userauth/auth/login", self.login)
self._register_auth_route_helper("/userauth/auth/logout", self.logout)
```

### **API Key Protected Routes**
```python
# Requires valid API key
self._register_auth_route_helper("/keyauth/users/create", self.create_user)
self._register_auth_route_helper("/keyauth/users/search", self.search_users)
self._register_auth_route_helper("/keyauth/admin/stats", self.get_stats)
```

## 🔧 **Implementation Details**

### **BaseModule Changes**

The `BaseModule` class now includes two registration methods:

#### **`_register_auth_route_helper()`**
```python
def _register_auth_route_helper(self, route: str, view_func, methods: List[str] = None):
    """
    Smart route registration that automatically determines authentication based on route prefix.
    
    Authentication rules:
    - /userauth/* -> Requires JWT token
    - /keyauth/* -> Requires API key
    - /public/* -> No authentication required
    - All other routes -> No authentication required (public)
    """
    auth_type = None
    
    # Determine authentication type based on route prefix
    if route.startswith('/userauth/'):
        auth_type = 'jwt'
    elif route.startswith('/keyauth/'):
        auth_type = 'key'
    elif route.startswith('/public/'):
        auth_type = None  # Explicitly public
    else:
        auth_type = None  # Default to public
    
    # Register with determined auth type
    self._register_route_helper(route, view_func, methods, auth_type)
```

#### **Enhanced `_register_route_helper()`**
```python
def _register_route_helper(self, route: str, view_func, methods: List[str] = None, auth: str = None):
    """
    Helper method to register a route and track it.
    
    :param auth: Authentication type - 'jwt', 'key', or None for public
    """
    # Register with Flask
    self.app.add_url_rule(route, view_func=view_func, methods=methods)
    
    # Track route with authentication info
    route_info = (route, view_func.__name__, methods, auth)
    self.registered_routes.append(route_info)
    
    auth_info = f" (auth: {auth})" if auth else " (public)"
    custom_log(f"Module {self.module_name} registered route: {route}{auth_info}")
```

### **Authentication Middleware**

The authentication middleware now uses route-based rules:

```python
def authenticate_request():
    """Smart authentication middleware based on route prefixes."""
    
    # Determine authentication requirements based on route prefix
    auth_required = None
    
    # Check new route-based authentication rules
    if request.path.startswith('/userauth/'):
        auth_required = 'jwt'
    elif request.path.startswith('/keyauth/'):
        auth_required = 'key'
    elif request.path.startswith('/public/'):
        auth_required = None  # Explicitly public
    else:
        # Check legacy routes for backward compatibility
        # ... legacy logic ...
    
    # Handle authentication based on type
    if auth_required == 'jwt':
        # Validate JWT token
    elif auth_required == 'key':
        # Validate API key
    # ... etc
```

## 🔄 **Migration Guide**

### **From Old System to New System**

#### **Before (Hardcoded Routes)**
```python
# In app_manager.py - hardcoded lists
public_routes = ['/health', '/status', '/info']
forward_routes = ['/users', '/auth']

# In middleware - complex logic
if request.path in public_routes:
    return None
elif request.path.startswith('/users/'):
    # Forward logic
```

#### **After (Route-Based)**
```python
# In module - simple registration
def register_routes(self):
    self._register_auth_route_helper("/public/health", self.health_check)
    self._register_auth_route_helper("/userauth/users/profile", self.get_profile)
    self._register_auth_route_helper("/keyauth/users/create", self.create_user)

# Middleware automatically handles auth based on route prefix
```

### **Clean Implementation**

Since there's no frontend yet, we've implemented a clean system:

1. **No backward compatibility** - fresh start with clean architecture
2. **Route-based authentication** - automatic based on prefixes
3. **Simple and maintainable** - no complex legacy logic

## 🧪 **Testing**

### **Test Script**
Run the test script to verify the new system:

```bash
cd python_base_04_external
python test_new_routes.py
```

### **Manual Testing**

#### **Public Routes**
```bash
curl http://localhost:8081/public/users/info
# Should return 200 OK
```

#### **JWT Routes**
```bash
curl http://localhost:8081/userauth/users/profile
# Should return 401 Unauthorized (JWT_REQUIRED)

curl -H "Authorization: Bearer valid_token" http://localhost:8081/userauth/users/profile
# Should return 200 OK (if valid token)
```

#### **API Key Routes**
```bash
curl -X POST http://localhost:8081/keyauth/users/create \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser"}'
# Should return 401 Unauthorized (API_KEY_REQUIRED)

curl -X POST http://localhost:8081/keyauth/users/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: valid_key" \
  -d '{"email":"test@example.com","username":"testuser"}'
# Should return 201 Created (if valid key)
```

## 📊 **Benefits**

### **1. Simplified Route Registration**
- No need to hardcode route lists
- Automatic authentication determination
- Clear and consistent naming

### **2. Better Maintainability**
- Authentication rules are co-located with routes
- Easy to understand and modify
- Reduced complexity in middleware

### **3. Improved Developer Experience**
- Intuitive route naming
- Clear authentication requirements
- Self-documenting code

### **4. Backward Compatibility**
- Existing routes continue to work
- Gradual migration possible
- No breaking changes

## 🚀 **Best Practices**

### **1. Use Descriptive Route Prefixes**
```python
# Good
/userauth/users/profile
/keyauth/admin/stats
/public/health

# Avoid
/auth/profile  # Unclear which auth type
/admin/stats   # No prefix
```

### **2. Group Related Routes**
```python
def register_routes(self):
    # Public routes
    self._register_auth_route_helper("/public/health", self.health_check)
    self._register_auth_route_helper("/public/info", self.get_info)
    
    # User authentication routes
    self._register_auth_route_helper("/userauth/users/profile", self.get_profile)
    self._register_auth_route_helper("/userauth/users/settings", self.get_settings)
    
    # API key routes
    self._register_auth_route_helper("/keyauth/users/create", self.create_user)
    self._register_auth_route_helper("/keyauth/users/search", self.search_users)
```

### **3. Use Explicit Registration When Needed**
```python
# For custom authentication logic
self._register_route_helper("/custom/route", self.handler, auth="jwt")
```

## 🔍 **Debugging**

### **Check Registered Routes**
```bash
curl http://localhost:8081/modules/status
```

### **View Route Authentication**
Routes are logged with authentication info:
```
Module UserManagementModule registered route: /userauth/users/profile (auth: jwt)
Module UserManagementModule registered route: /keyauth/users/create (auth: key)
Module UserManagementModule registered route: /public/users/info (public)
```

### **Common Issues**

1. **Route not found**: Check if route is properly registered
2. **Authentication error**: Verify route prefix matches expected auth type
3. **Legacy route issues**: Check backward compatibility logic

## 📝 **Summary**

The new route registration system provides:

- ✅ **Automatic authentication determination** based on route prefixes
- ✅ **Simplified route registration** without hardcoded lists
- ✅ **Better maintainability** and developer experience
- ✅ **Backward compatibility** with existing routes
- ✅ **Clear and consistent** authentication requirements
- ✅ **Self-documenting** route structure

This system makes it much easier to add new routes with the correct authentication requirements without modifying the authentication middleware. 