# Hooks Manager Documentation

## Overview
The `HooksManager` is a singleton class that implements a hook system for the application. It allows for the registration and triggering of callbacks at specific points in the application lifecycle, with support for priority-based execution.

## Key Features
- Singleton pattern implementation
- Priority-based hook execution
- Hook registration and deregistration
- Callback management
- Comprehensive logging

## Class Structure

### HooksManager
The main hook management class.

#### Properties
- `_log`: Static logger instance
- `_instance`: Static singleton instance
- `_hooks`: Private map storing registered hooks

#### Methods
- `registerHook`: Registers a new hook callback
- `triggerHook`: Triggers all callbacks for a hook
- `deregisterHook`: Removes all callbacks for a hook
- `deregisterCallback`: Removes a specific callback from a hook

## Usage Examples

### Registering a Hook
```dart
final hooksManager = HooksManager();
hooksManager.registerHook('app_startup', () {
  // Hook callback logic
}, priority: 5);
```

### Triggering a Hook
```dart
HooksManager().triggerHook('app_startup');
```

### Deregistering a Hook
```dart
// Deregister all callbacks for a hook
HooksManager().deregisterHook('app_startup');

// Deregister a specific callback
HooksManager().deregisterCallback('app_startup', myCallback);
```

## Hook System Details

### Priority System
- Lower priority numbers execute first
- Default priority is 10
- Hooks are automatically sorted by priority
- Multiple callbacks can have the same priority

### Hook Registration Process
1. Priority validation
2. Duplicate checking
3. Callback storage
4. Priority-based sorting
5. Logging

## Best Practices
1. Use meaningful hook names
2. Set appropriate priorities
3. Clean up hooks when no longer needed
4. Handle hook execution errors
5. Use logging for debugging

## Error Handling
The HooksManager includes:
- Duplicate callback prevention
- Empty hook handling
- Comprehensive logging
- Graceful error recovery

## Dependencies
- `../../tools/logging/logger.dart`

## Hook Lifecycle
1. Registration
2. Priority sorting
3. Execution
4. Cleanup

## Common Hook Names
- `app_startup`: Application initialization
- `reg_nav`: Navigation registration
- Custom hooks can be defined as needed

## Integration with Other Components
The HooksManager works with:
- `Logger`: For logging operations
- `PluginManager`: For plugin lifecycle hooks
- `AppManager`: For application lifecycle hooks

## Performance Considerations
- Hooks are stored in memory
- Priority sorting happens on registration
- Callback execution is synchronous
- Large numbers of hooks may impact performance 