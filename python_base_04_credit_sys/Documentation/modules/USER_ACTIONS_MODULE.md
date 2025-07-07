# User Actions Module

## 📋 Overview

The User Actions Module is a **declarative, configuration-driven system** that provides a flexible and extensible way to define and execute user-related operations. It uses YAML configuration files to define actions declaratively, making it easy to add new functionality without modifying code.

## 🏗️ Architecture

### Core Components

1. **Declarative Configuration** (`actions.yaml`)
2. **Action Executor** (`user_actions_main.py`)
3. **Database Integration** (via Database Manager)
4. **REST API Endpoints**

### Module Structure

```
core/modules/user_actions/
├── declarations/
│   └── actions.yaml          # Action definitions
├── user_actions_main.py      # Main module logic
└── __init__.py
```

## 🔧 How It Works

### 1. Declarative Action Definition

Actions are defined in `actions.yaml` with a clear, structured format:

```yaml
actions:
  action_name:
    description: "What this action does"
    type: "function|database|external_api"
    # Type-specific configuration follows
```

### 2. Action Types

The module supports three types of actions:

#### **Function Actions** (`type: "function"`)
- Execute custom Python functions
- Direct access to database managers
- Full control over logic and data processing

```yaml
get_user_profile:
  description: "Retrieve user profile information"
  type: "function"
  function: "get_user_profile"
  required_params: ["user_id"]
  optional_params: ["include_preferences", "include_activity"]
```

#### **Database Actions** (`type: "database"`)
- Direct database operations (CRUD)
- Automatic parameter validation
- Built-in error handling

```yaml
log_user_activity:
  description: "Log user activity for analytics"
  type: "database"
  operation: "insert"
  collection: "user_activities"
  required_params: ["user_id", "activity_type"]
  optional_params: ["metadata", "timestamp"]
```

#### **External API Actions** (`type: "external_api"`)
- HTTP requests to external services
- Configurable endpoints and methods
- Response handling

```yaml
send_user_notification:
  description: "Send a notification to user"
  type: "external_api"
  url: "https://api.notifications.com/send"
  method: "POST"
  required_params: ["user_id", "message"]
  optional_params: ["priority", "channel"]
```

### 3. Parameter System

#### **Required Parameters**
- Must be provided in the request
- Validated before action execution
- Clear error messages if missing

#### **Optional Parameters**
- Can be omitted from request
- Default values can be specified
- Conditional logic support

#### **Parameter Validation**
```python
# Automatic validation based on YAML definition
required_params: ["user_id", "email"]
optional_params: ["preferences", "notify_user"]
```

### 4. Execution Flow

```
1. Request Received
   ↓
2. Load Action Configuration (YAML)
   ↓
3. Validate Parameters
   ↓
4. Determine Action Type
   ↓
5. Execute Action:
   ├── Function: Call Python method
   ├── Database: Execute CRUD operation
   └── External API: Make HTTP request
   ↓
6. Format Response
   ↓
7. Return Result
```

## 📊 Current Actions

### Available Actions (6 total)

#### **1. get_user_profile** (Function)
- **Purpose**: Retrieve complete user profile with wallet information
- **Required**: `user_id`
- **Optional**: `include_preferences`, `include_activity`
- **Returns**: User data, wallet balance, preferences

#### **2. update_user_preferences** (Function)
- **Purpose**: Update user preferences and settings
- **Required**: `user_id`, `preferences`
- **Optional**: `notify_user`
- **Returns**: Updated user data

#### **3. send_user_notification** (External API)
- **Purpose**: Send notifications via external service
- **Required**: `user_id`, `message`
- **Optional**: `priority`, `channel`
- **Returns**: Notification status

#### **4. log_user_activity** (Database)
- **Purpose**: Log user activities for analytics
- **Required**: `user_id`, `activity_type`
- **Optional**: `metadata`, `timestamp`
- **Returns**: Log entry confirmation

#### **5. validate_user_permissions** (Function)
- **Purpose**: Check user permissions for specific operations
- **Required**: `user_id`, `permission`
- **Optional**: `resource_id`
- **Returns**: Permission status

#### **6. find_users** (Database)
- **Purpose**: Search users with filters
- **Required**: `query` (MongoDB query object)
- **Optional**: `limit`, `sort`
- **Returns**: Matching users list

## 🔌 API Endpoints

### List All Actions
```http
GET /actions
```
Returns all available actions with their configurations.

### Execute Action
```http
POST /actions/{action_name}
Content-Type: application/json

{
  "user_id": "507f1f77bcf86cd799439011",
  "include_preferences": true
}
```

## 💾 Database Integration

### Database Manager Access
The module integrates with the Database Manager to perform real database operations:

```python
# Database manager is initialized in constructor
self.database_manager = app_manager.get_module("database_manager")
```

### Supported Operations
- **Insert**: Add new documents to collections
- **Find**: Query documents with filters
- **Update**: Modify existing documents
- **Delete**: Remove documents

### Collection Access
- `users`: User profiles and data
- `wallets`: User wallet information
- `user_activities`: Activity logging
- `audit_logs`: System audit trail

## 🛠️ Adding New Actions

### Step 1: Define Action in YAML
```yaml
# Add to actions.yaml
new_action:
  description: "Perform a new operation"
  type: "function"
  function: "new_action_function"
  required_params: ["param1", "param2"]
  optional_params: ["optional_param"]
  examples:
    - description: "Example usage"
      request: '{"param1": "value1", "param2": "value2"}'
```

### Step 2: Implement Function (if Function Type)
```python
def _new_action_function(self, request_data: Dict) -> Dict:
    """Execute the new action."""
    param1 = request_data.get("param1")
    param2 = request_data.get("param2")
    
    # Your logic here
    result = self.database_manager.find_documents("collection", {"field": param1})
    
    return {
        "status": "success",
        "data": result
    }
```

### Step 3: Test the Action
```bash
curl -X POST http://localhost:8080/actions/new_action \
  -H "Content-Type: application/json" \
  -d '{"param1": "value1", "param2": "value2"}'
```

## 🔍 Error Handling

### Parameter Validation
- Missing required parameters return 400 error
- Invalid parameter types are caught
- Clear error messages provided

### Database Errors
- Connection failures handled gracefully
- Query errors logged and reported
- ObjectId conversion errors caught

### External API Errors
- Network timeouts handled
- HTTP error responses processed
- Retry logic for transient failures

## 📈 Monitoring and Logging

### Action Execution Logging
```python
custom_log(f"Executing action: {action_name}")
custom_log(f"Action parameters: {request_data}")
custom_log(f"Action result: {result}")
```

### Performance Metrics
- Action execution time tracking
- Database query performance
- External API response times

## 🔒 Security Considerations

### Input Validation
- All parameters validated against YAML schema
- SQL injection prevention (MongoDB queries)
- XSS protection for user inputs

### Authentication
- User ID validation before operations
- Permission checking for sensitive actions
- Audit logging for all operations

### Data Sanitization
- ObjectId conversion for MongoDB
- JSON serialization safety
- Error message sanitization

## 🧪 Testing

### Unit Tests
```python
def test_get_user_profile():
    """Test user profile retrieval."""
    action = UserActionsModule()
    result = action._get_user_profile({"user_id": "test_id"})
    assert result["status"] == "success"
```

### Integration Tests
```bash
# Test action execution via API
curl -X POST http://localhost:8080/actions/get_user_profile \
  -H "Content-Type: application/json" \
  -d '{"user_id": "507f1f77bcf86cd799439011"}'
```

### Load Testing
```bash
# Test multiple concurrent requests
ab -n 100 -c 10 -p test_data.json \
  -T application/json \
  http://localhost:8080/actions/get_user_profile
```

## 📚 Examples

### Function Action Example
```yaml
get_user_wallet:
  description: "Get user wallet information"
  type: "function"
  function: "get_user_wallet"
  required_params: ["user_id"]
  examples:
    - description: "Get wallet for user"
      request: '{"user_id": "507f1f77bcf86cd799439011"}'
```

### Database Action Example
```yaml
create_user_transaction:
  description: "Create a new user transaction"
  type: "database"
  operation: "insert"
  collection: "transactions"
  required_params: ["user_id", "amount", "type"]
  optional_params: ["description", "metadata"]
```

### External API Action Example
```yaml
send_email_notification:
  description: "Send email via external service"
  type: "external_api"
  url: "https://api.emailservice.com/send"
  method: "POST"
  required_params: ["to", "subject", "body"]
  optional_params: ["cc", "bcc", "attachments"]
```

## 🚀 Best Practices

### 1. Action Design
- Keep actions focused and single-purpose
- Use descriptive names and descriptions
- Provide clear examples in YAML

### 2. Parameter Design
- Minimize required parameters
- Use sensible defaults for optional parameters
- Validate parameter types and ranges

### 3. Error Handling
- Always return structured error responses
- Log errors with sufficient context
- Provide helpful error messages

### 4. Performance
- Use database indexes for queries
- Implement caching where appropriate
- Monitor action execution times

### 5. Security
- Validate all inputs
- Sanitize outputs
- Log security-relevant events

## 🔄 Future Enhancements

### Planned Features
- **Action Chaining**: Execute multiple actions in sequence
- **Conditional Logic**: Execute actions based on conditions
- **Scheduled Actions**: Execute actions at specific times
- **Action Templates**: Reusable action configurations
- **Webhook Support**: Trigger actions from external events

### Performance Improvements
- **Action Caching**: Cache frequently used actions
- **Batch Operations**: Execute multiple operations efficiently
- **Async Support**: Non-blocking action execution

## 📞 Support

For questions or issues with the User Actions Module:

1. Check the logs in `python_base_04_k8s/tools/logger/server.log`
2. Test individual actions via the API endpoints
3. Review the YAML configuration for syntax errors
4. Verify database connectivity and permissions

---

**Last Updated**: January 2025  
**Version**: 1.0.0  
**Maintainer**: Development Team 