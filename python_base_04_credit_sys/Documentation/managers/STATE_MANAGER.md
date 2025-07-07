# State Manager

## 🏗️ Introduction

The **StateManager** is a core infrastructure component that provides centralized state management capabilities for the Flask Credit System. It enables modules to maintain, track, and transition between different states with full history tracking, validation, and callback support.

**Singleton Pattern**: The StateManager implements the singleton pattern, ensuring only one instance exists throughout the application lifecycle. This provides global state consistency and prevents state fragmentation across different parts of the application.

## 📋 Overview

The StateManager provides a robust foundation for managing application state across different domains:

- **User States**: User sessions, preferences, and account status
- **Transaction States**: Payment processing, verification, and completion states  
- **Subscription States**: Plan management, billing cycles, and access control
- **Feature States**: Feature flags, A/B testing, and rollout management
- **Session States**: Authentication sessions and security states

## 🏛️ Architecture

### State Structure
```python
{
    "state_id": "unique_identifier",
    "name": "descriptive_name",
    "type": "USER|TRANSACTION|SUBSCRIPTION|FEATURE|SESSION",
    "data": {
        # Domain-specific state data
        "user_id": "12345",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z"
    },
    "metadata": {
        "version": "1.0",
        "environment": "production",
        "created_by": "system"
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

### State Types
```python
class StateType(Enum):
    USER = "user"           # User-related states
    TRANSACTION = "transaction"  # Payment/transaction states
    SUBSCRIPTION = "subscription"  # Subscription management
    FEATURE = "feature"     # Feature flags and rollouts
    SESSION = "session"     # Authentication sessions
```

### State Transitions
```python
class StateTransition(Enum):
    CREATE = "create"       # Initial state creation
    UPDATE = "update"       # State modification
    ACTIVATE = "activate"   # Activate/start state
    SUSPEND = "suspend"     # Temporarily suspend
    RESUME = "resume"       # Resume suspended state
    EXPIRE = "expire"       # Mark as expired
    DELETE = "delete"       # Remove state
```

## ⚙️ Core Features

### 1. State Registration and Management
**Purpose**: Create and manage state entries with validation and metadata

**Key Features**:
- Unique state ID generation and validation
- State type enforcement and validation
- Automatic timestamp management
- Metadata tracking and versioning

**Usage**:
```python
# Get singleton instance (recommended)
state_manager = StateManager.get_instance()

# Or create instance (returns same singleton)
state_manager = StateManager()

# Register a new state
user_state = {
    "name": "user_account_state",
    "type": StateType.USER.value,
    "data": {
        "user_id": "12345",
        "status": "active",
        "email": "user@example.com"
    },
    "metadata": {
        "version": "1.0",
        "environment": "production"
    }
}

result = state_manager.register_state(
    state_id="user_12345",
    state_type=StateType.USER,
    initial_data=user_state
)
```

### 2. State Retrieval and Querying
**Purpose**: Efficiently retrieve states with filtering and search capabilities

**Key Features**:
- Single state retrieval by ID
- Bulk state retrieval by type
- State filtering and search
- Pagination support

**Usage**:
```python
# Get single state
user_state = state_manager.get_state("user_12345")

# Get all user states
user_states = state_manager.get_states_by_type(StateType.USER)

# Search states with filters
active_users = state_manager.search_states(
    state_type=StateType.USER,
    filters={"data.status": "active"}
)
```

### 3. State Transitions and Updates
**Purpose**: Manage state changes with validation and history tracking

**Key Features**:
- Validated state transitions
- Automatic history tracking
- Transition metadata and timestamps
- Rollback capabilities

**Usage**:
```python
# Update state with transition
updated_data = {
    "name": "user_account_state",
    "type": StateType.USER.value,
    "data": {
        "user_id": "12345",
        "status": "suspended",
        "suspended_reason": "payment_failed"
    }
}

result = state_manager.update_state(
    state_id="user_12345",
    new_data=updated_data,
    transition=StateTransition.SUSPEND
)
```

### 4. State History and Audit Trail
**Purpose**: Maintain complete audit trail of all state changes

**Key Features**:
- Complete state change history
- Transition type tracking
- Timestamp preservation
- Change metadata storage

**Usage**:
```python
# Get state history
history = state_manager.get_state_history("user_12345")

# Get recent changes
recent_changes = state_manager.get_recent_changes(
    state_id="user_12345",
    limit=10
)

# Get changes by transition type
suspensions = state_manager.get_changes_by_transition(
    state_id="user_12345",
    transition_type=StateTransition.SUSPEND
)
```

### 5. State Callbacks and Event Handling
**Purpose**: React to state changes with custom business logic

**Key Features**:
- Custom callback registration
- Event-driven state changes
- Asynchronous callback processing
- Error handling and retry logic

**Usage**:
```python
# Define callback function
def user_suspended_callback(state_id: str, old_state: dict, new_state: dict, transition_type: str):
    # Send notification to user
    notification_service.send_suspension_notice(state_id)
    
    # Update external systems
    billing_service.suspend_billing(state_id)

# Register callback
state_manager.register_callback("user_suspended", user_suspended_callback)

# Callback is automatically triggered on state transitions
```

### 6. State Validation and Constraints
**Purpose**: Ensure data integrity and business rule compliance

**Key Features**:
- State schema validation
- Business rule enforcement
- Transition validation
- Data type checking

**Usage**:
```python
# Custom validation function
def validate_user_state(state_data: dict) -> bool:
    required_fields = ["user_id", "status", "email"]
    return all(field in state_data.get("data", {}) for field in required_fields)

# Register validation
state_manager.register_validator(StateType.USER, validate_user_state)
```

## 🔧 Integration with Other Managers

### Singleton Pattern Usage
```python
# Recommended: Get singleton instance with managers
state_manager = StateManager.get_instance(
    redis_manager=app_manager.redis_manager,
    database_manager=app_manager.database_manager
)

# Alternative: Create instance (returns same singleton)
state_manager = StateManager(
    redis_manager=app_manager.redis_manager,
    database_manager=app_manager.database_manager
)

# Verify singleton behavior
state_manager_1 = StateManager.get_instance()
state_manager_2 = StateManager.get_instance()
assert state_manager_1 is state_manager_2  # Same instance
```

### Redis Integration
```python
# State caching for performance
state_manager = StateManager.get_instance(
    redis_manager=app_manager.redis_manager
)
```

### Database Integration
```python
# Persistent state storage
state_manager = StateManager.get_instance(
    database_manager=app_manager.database_manager
)
```

### Testing Support
```python
# Reset singleton for clean testing
StateManager.reset_instance()

# Run tests with fresh instance
state_manager = StateManager.get_instance()
```

## 📊 Performance and Scalability

### Caching Strategy
- **Redis Caching**: Frequently accessed states cached in Redis
- **TTL Management**: Configurable cache expiration
- **Cache Invalidation**: Automatic cache updates on state changes

### Database Optimization
- **Indexing**: Optimized indexes on state_id, type, and timestamps
- **Pagination**: Efficient handling of large state collections
- **Connection Pooling**: Reuse database connections

### Memory Management
- **Lazy Loading**: States loaded on-demand
- **Memory Limits**: Configurable memory usage limits
- **Garbage Collection**: Automatic cleanup of expired states

## 🧪 Testing and Validation

### Test Coverage
The StateManager includes comprehensive test coverage:

```python
# Run all state manager tests
python tools/tests/test_state_manager.py
```

### Test Categories
1. **Basic Operations**: CRUD operations and validation
2. **State Transitions**: Transition logic and validation
3. **History Tracking**: Audit trail verification
4. **Callback Testing**: Event handling verification
5. **Performance Tests**: Load and stress testing

### Example Test
```python
def test_user_state_lifecycle():
    """Test complete user state lifecycle."""
    state_manager = StateManager()
    
    # Create user state
    user_state = create_user_state("test_user")
    state_manager.register_state("test_user", StateType.USER, user_state)
    
    # Activate user
    state_manager.update_state("test_user", activate_user_data(), StateTransition.ACTIVATE)
    
    # Suspend user
    state_manager.update_state("test_user", suspend_user_data(), StateTransition.SUSPEND)
    
    # Resume user
    state_manager.update_state("test_user", resume_user_data(), StateTransition.RESUME)
    
    # Verify history
    history = state_manager.get_state_history("test_user")
    assert len(history) == 4  # create + activate + suspend + resume
```

## 🚀 Usage Examples

### User Management
```python
# User registration flow
def register_user(user_data: dict):
    state_manager = StateManager()
    
    # Create initial user state
    initial_state = {
        "name": "user_registration",
        "type": StateType.USER.value,
        "data": {
            "user_id": user_data["id"],
            "status": "pending_verification",
            "email": user_data["email"]
        }
    }
    
    state_manager.register_state(
        state_id=user_data["id"],
        state_type=StateType.USER,
        initial_data=initial_state
    )
    
    # Send verification email
    send_verification_email(user_data["email"])

# User verification callback
def on_user_verified(user_id: str):
    state_manager = StateManager()
    
    updated_state = {
        "name": "user_registration",
        "type": StateType.USER.value,
        "data": {
            "user_id": user_id,
            "status": "active",
            "verified_at": datetime.now().isoformat()
        }
    }
    
    state_manager.update_state(
        state_id=user_id,
        new_data=updated_state,
        transition=StateTransition.ACTIVATE
    )
```

### Transaction Processing
```python
# Transaction state management
def process_transaction(transaction_id: str, amount: float):
    state_manager = StateManager()
    
    # Create transaction state
    transaction_state = {
        "name": "payment_transaction",
        "type": StateType.TRANSACTION.value,
        "data": {
            "transaction_id": transaction_id,
            "amount": amount,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
    }
    
    state_manager.register_state(
        state_id=transaction_id,
        state_type=StateType.TRANSACTION,
        initial_data=transaction_state
    )
    
    # Process payment
    payment_result = payment_processor.process(transaction_id, amount)
    
    if payment_result.success:
        # Update to completed
        completed_state = {
            "name": "payment_transaction",
            "type": StateType.TRANSACTION.value,
            "data": {
                "transaction_id": transaction_id,
                "amount": amount,
                "status": "completed",
                "completed_at": datetime.now().isoformat()
            }
        }
        
        state_manager.update_state(
            state_id=transaction_id,
            new_data=completed_state,
            transition=StateTransition.ACTIVATE
        )
    else:
        # Update to failed
        failed_state = {
            "name": "payment_transaction",
            "type": StateType.TRANSACTION.value,
            "data": {
                "transaction_id": transaction_id,
                "amount": amount,
                "status": "failed",
                "error": payment_result.error,
                "failed_at": datetime.now().isoformat()
            }
        }
        
        state_manager.update_state(
            state_id=transaction_id,
            new_data=failed_state,
            transition=StateTransition.EXPIRE
        )
```

## 🔒 Security Considerations

### Data Protection
- **Encryption**: Sensitive state data encrypted at rest
- **Access Control**: Role-based access to state operations
- **Audit Logging**: Complete audit trail for compliance

### Validation
- **Input Validation**: All state data validated before storage
- **Schema Enforcement**: Strict schema validation for state types
- **Transition Validation**: Business rule enforcement for state changes

### Performance
- **Rate Limiting**: Prevent abuse of state operations
- **Resource Limits**: Configurable limits on state size and count
- **Timeout Handling**: Graceful handling of slow operations

## 📈 Monitoring and Observability

### Metrics
- **State Operations**: Count of create, read, update, delete operations
- **Transition Rates**: Frequency of state transitions
- **Performance**: Response times and throughput
- **Error Rates**: Failed operations and error types

### Logging
```python
# Structured logging for state operations
state_manager.log_state_operation(
    operation="state_update",
    state_id="user_12345",
    transition_type="activate",
    duration_ms=45
)
```

### Health Checks
```python
# State manager health status
health_status = state_manager.get_health_status()
# Returns: {"status": "healthy", "state_count": 1250, "cache_hit_rate": 0.95}
```

## 🔄 Migration and Compatibility

### Version Compatibility
- **Backward Compatibility**: Supports existing state formats
- **Schema Evolution**: Graceful handling of schema changes
- **Data Migration**: Tools for migrating existing state data

### Breaking Changes
- **State ID Format**: Changes to state ID generation
- **Schema Updates**: New required fields or validation rules
- **API Changes**: Modified method signatures or return values

---

*Last Updated: 2024-07-03*
*State Manager Version: 1.0*
*Compatible with: Flask Credit System v2.0+* 