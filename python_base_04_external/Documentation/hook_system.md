# Hook System Documentation

## Overview

The hook system in `python_base_04_external` provides an event-driven architecture that allows modules to communicate and react to system events without tight coupling. This enables loose coupling between modules while maintaining a clean, extensible architecture.

## Architecture

### Core Components

1. **HooksManager** (`core/managers/hooks_manager.py`)
   - Central hook registry and management
   - Priority-based callback execution
   - Context filtering for targeted callbacks
   - Comprehensive logging and error handling

2. **AppManager Integration** (`core/managers/app_manager.py`)
   - Clean interface for modules to register and trigger hooks
   - Delegates to HooksManager for actual operations
   - Provides consistent API across the application

3. **Module Integration**
   - Modules register callbacks during initialization
   - Modules trigger hooks when events occur
   - Priority-based execution ensures proper order

## Hook System Features

### Priority System
- Lower numbers = higher priority
- Callbacks execute in priority order
- Default priority is 10
- Range: 1-100 (1 = highest, 100 = lowest)

### Context Filtering
- Callbacks can be filtered by context
- Allows targeted execution for specific scenarios
- Useful for module-specific operations

### Error Handling
- Graceful handling of missing hooks
- Comprehensive logging for debugging
- Non-blocking execution (one failed callback doesn't stop others)

## Current Implementation

### User Creation Hook

The system currently implements a `user_created` hook that triggers when a new user is successfully created.

#### Hook Trigger (UserManagementModule)
```python
# Trigger user_created hook for other modules to listen to
if self.app_manager:
    hook_data = {
        'user_id': user_id,
        'username': username,
        'email': email,
        'user_data': user_data,
        'wallet_id': wallet_id,
        'created_at': current_time.isoformat()
    }
    self.app_manager.trigger_hook("user_created", hook_data)
```

#### Hook Callbacks

1. **WalletModule** (Priority: 5)
   - Initializes wallet module data in user document
   - Sets initial balance to 0 credits
   - Updates user document with embedded wallet data
   - Follows modular database structure

2. **CommunicationsModule** (Priority: 10)
   - Sends welcome notification
   - Creates notification record in database
   - Logs welcome message

## Usage Examples

### Registering a Hook Callback

```python
def _register_hooks(self):
    """Register hooks for user-related events."""
    if self.app_manager:
        # Register callback for user creation
        self.app_manager.register_hook_callback(
            "user_created", 
            self._on_user_created, 
            priority=5, 
            context="wallet"
        )

def _on_user_created(self, hook_data):
    """Handle user creation event."""
    user_id = hook_data.get('user_id')
    username = hook_data.get('username')
    # Process the event...
```

### Triggering a Hook

```python
# Trigger hook with data
hook_data = {
    'user_id': user_id,
    'username': username,
    'email': email,
    # ... other data
}
self.app_manager.trigger_hook("user_created", hook_data)
```

### Registering a New Hook Type

```python
# Register a new hook type
self.app_manager.register_hook("payment_processed")

# Register callbacks for the new hook
self.app_manager.register_hook_callback("payment_processed", self._on_payment_processed)
```

## Hook Data Structure

### user_created Hook
```python
{
    'user_id': 'user_id_string',
    'username': 'username_string',
    'email': 'email@example.com',
    'user_data': {
        # Complete user data object with modular structure
        'modules': {
            'wallet': {
                'enabled': True,
                'balance': 0,
                'currency': 'credits',
                'last_updated': '2024-01-01T12:00:00.000Z'
            }
        }
    },
    'created_at': '2024-01-01T12:00:00.000Z'
}
```

## Best Practices

### 1. Hook Naming
- Use descriptive, action-oriented names
- Follow snake_case convention
- Be specific about the event (e.g., `user_created`, `payment_failed`)

### 2. Priority Management
- Use priority 1-5 for critical operations (database setup, security)
- Use priority 6-10 for core business logic
- Use priority 11-20 for notifications and logging
- Use priority 21+ for analytics and monitoring

### 3. Error Handling
- Always wrap hook callbacks in try-catch blocks
- Log errors but don't let them break the system
- Return early if required data is missing

### 4. Data Validation
- Validate hook data before processing
- Use safe dictionary access (`.get()` method)
- Provide default values for optional fields

## Testing

### Test Script
Run the test script to verify hook functionality:

```bash
python test_hook_system.py
```

This script:
1. Creates a test user
2. Observes hook triggers
3. Verifies database changes
4. Shows hook execution order

### Expected Output
```
🎣 Testing Hook System - User Creation Event
📝 Creating test user: testuser_1234567890
📧 Email: testuser_1234567890@example.com

📤 POST /public/register: 201
✅ User created successfully!

🎣 Expected Hook Triggers:
  1. UserManagementModule: Triggers 'user_created' hook
  2. WalletModule: Creates wallet for new user (priority 5)
  3. CommunicationsModule: Sends welcome notification (priority 10)
  4. TransactionsModule: Creates initial transaction record (priority 15)

📊 Database check results:
   - Notifications: 1 found
   - Wallets: 1 found
   - Transactions: 1 found
```

## Future Enhancements

### Potential New Hooks

1. **payment_processed** - When payment is completed
2. **user_login** - When user logs in
3. **user_logout** - When user logs out
4. **credit_purchase** - When credits are purchased
5. **system_error** - When system errors occur
6. **module_initialized** - When modules are initialized

### Advanced Features

1. **Async Hook Processing** - Non-blocking hook execution
2. **Hook Retry Logic** - Retry failed hook callbacks
3. **Hook Metrics** - Track hook performance and usage
4. **Hook Validation** - Validate hook data schemas
5. **Hook Chaining** - Chain multiple hooks together

## Troubleshooting

### Common Issues

1. **Hook not triggering**
   - Check if hook is properly registered
   - Verify app_manager is available
   - Check logs for error messages

2. **Callback not executing**
   - Verify callback is registered with correct hook name
   - Check priority and context settings
   - Ensure callback function exists and is callable

3. **Database operations failing**
   - Check database connection
   - Verify queue system is working
   - Check for permission issues

### Debug Commands

```python
# Check registered hooks
print(self.app_manager.hooks_manager.hooks)

# Check specific hook callbacks
hook_name = "user_created"
callbacks = self.app_manager.hooks_manager.hooks.get(hook_name, [])
for callback in callbacks:
    print(f"Priority: {callback['priority']}, Context: {callback['context']}")
```

## Conclusion

The hook system provides a powerful, flexible foundation for event-driven architecture in the credit system. It enables loose coupling between modules while maintaining clean, testable code. The current implementation demonstrates the system's capabilities with the `user_created` hook, and the architecture supports easy extension for future requirements. 