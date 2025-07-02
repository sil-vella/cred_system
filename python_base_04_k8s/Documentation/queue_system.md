# Queue System Documentation

## Overview

The Queue System provides asynchronous processing of database operations to prevent overwhelming the application with high-volume database inputs. This is especially important for credit systems where user credit purchases, calculations, and other operations need to be processed reliably without blocking user requests.

## Architecture

### Components

1. **QueueManager**: Central queue management system using Redis for persistence
2. **Background Workers**: Thread-based workers that process queued tasks
3. **Priority Queues**: Multiple priority levels (LOW, NORMAL, HIGH, CRITICAL)
4. **Task Handlers**: Custom handlers for complex operations or default database operations

### Queue Types

- **default**: Normal priority operations (user registrations, basic updates)
- **high_priority**: Critical operations (credit updates, balance changes)
- **low_priority**: Background tasks (analytics, cleanup, notifications)

## Key Features

### 1. Asynchronous Processing
- Database operations are queued and processed in the background
- Users receive immediate responses while operations are processed
- Prevents request timeouts and improves user experience

### 2. Priority-Based Processing
- Critical operations (credit updates) are processed first
- Background tasks don't block important operations
- Configurable priority levels for different operation types

### 3. Fault Tolerance
- Automatic retry with exponential backoff
- Failed tasks are logged and can be manually reviewed
- Redis persistence ensures tasks survive application restarts

### 4. Monitoring & Statistics
- Real-time queue statistics
- Task status tracking
- Performance monitoring capabilities

## Usage Examples

### Basic Database Operations

```python
from core.managers.queue_manager import QueueManager, QueuePriority

queue_manager = QueueManager()

# Insert a user
task_data = {
    'operation': 'insert',
    'collection': 'users',
    'data': {
        'user_id': 'user123',
        'email': 'user@example.com',
        'credit_balance': 0
    }
}

task_id = queue_manager.enqueue(
    queue_name='default',
    task_type='user_registration',
    task_data=task_data,
    priority=QueuePriority.NORMAL
)
```

### Credit Purchase Processing

```python
# Queue a credit purchase (high priority)
purchase_data = {
    'operation': 'insert',
    'collection': 'credit_purchases',
    'data': {
        'user_id': 'user123',
        'amount': 100,
        'currency': 'USD',
        'transaction_id': 'txn_456'
    }
}

task_id = queue_manager.enqueue(
    queue_name='high_priority',
    task_type='credit_purchase',
    task_data=purchase_data,
    priority=QueuePriority.HIGH
)
```

### Custom Task Handlers

```python
def credit_calculation_handler(data, db_manager):
    """Custom handler for complex credit calculations."""
    user_id = data['user_id']
    
    # Get user's credit history
    purchases = db_manager.find_many('credit_purchases', {'user_id': user_id})
    usage = db_manager.find_many('credit_usage', {'user_id': user_id})
    
    # Calculate credit score
    total_purchased = sum(p['amount'] for p in purchases)
    total_used = sum(u['amount'] for u in usage)
    credit_score = calculate_score(total_purchased, total_used)
    
    # Store result
    result_data = {
        'user_id': user_id,
        'credit_score': credit_score,
        'calculated_at': datetime.utcnow()
    }
    
    return db_manager.insert('credit_calculations', result_data) is not None

# Register the handler
queue_manager.register_handler('credit_calculation', credit_calculation_handler)
```

## API Endpoints

### Queue a Task
```
POST /api/queue/enqueue
{
    "queue_name": "default",
    "task_type": "user_registration",
    "task_data": {
        "operation": "insert",
        "collection": "users",
        "data": {...}
    },
    "priority": 2,
    "delay": 0
}
```

### Check Task Status
```
GET /api/queue/status/{task_id}
```

### Get Queue Statistics
```
GET /api/queue/stats
GET /api/queue/stats/{queue_name}
```

### Example Endpoints
```
POST /api/queue/example/credit-purchase
POST /api/queue/example/user-registration
POST /api/queue/example/credit-update
```

## Configuration

### Queue Settings
```python
# In app_manager.py
self.queues = {
    'default': {'priority': QueuePriority.NORMAL, 'workers': 2},
    'high_priority': {'priority': QueuePriority.HIGH, 'workers': 3},
    'low_priority': {'priority': QueuePriority.LOW, 'workers': 1}
}
```

### Worker Configuration
- **default**: 2 workers for normal operations
- **high_priority**: 3 workers for critical operations
- **low_priority**: 1 worker for background tasks

## Benefits for Credit System

### 1. Prevents Database Overwhelm
- High-volume credit purchases are queued and processed asynchronously
- Database connections are managed efficiently
- Prevents connection pool exhaustion

### 2. Improves User Experience
- Users receive immediate confirmation for credit purchases
- No waiting for database operations to complete
- Better response times for API endpoints

### 3. Data Consistency
- Prevents race conditions in credit calculations
- Ensures atomic operations for balance updates
- Maintains data integrity under high load

### 4. Scalability
- Can handle traffic spikes gracefully
- Horizontal scaling by adding more workers
- Redis-based persistence for reliability

### 5. Monitoring & Debugging
- Track task processing times
- Monitor queue depths and worker performance
- Debug failed operations with detailed logging

## Best Practices

### 1. Task Design
- Keep tasks atomic and focused
- Use appropriate priority levels
- Include proper error handling

### 2. Monitoring
- Monitor queue depths regularly
- Set up alerts for failed tasks
- Track processing times and throughput

### 3. Error Handling
- Implement proper retry logic
- Log failed operations for debugging
- Provide fallback mechanisms

### 4. Performance
- Use appropriate queue sizes
- Monitor worker utilization
- Scale workers based on load

## Integration with Existing System

The Queue Manager integrates seamlessly with the existing architecture:

1. **AppManager**: Centralized initialization and management
2. **DatabaseManager**: Shared database connections
3. **RedisManager**: Queue persistence and task storage
4. **Rate Limiter**: Prevents queue abuse
5. **Monitoring**: Queue metrics and performance tracking

## Testing

Run the queue manager tests:
```bash
python -m unittest core.managers.tests.test_queue_manager
```

## Future Enhancements

1. **Dead Letter Queues**: For permanently failed tasks
2. **Task Scheduling**: Cron-like scheduling for recurring tasks
3. **Distributed Processing**: Multi-node queue processing
4. **Advanced Monitoring**: Grafana dashboards for queue metrics
5. **Task Dependencies**: Chained task execution
6. **Batch Processing**: Group similar tasks for efficiency 