# Module Manager Documentation

## Overview
The `ModuleManager` is a singleton class that manages application modules. It provides a centralized system for registering, retrieving, and managing module instances with support for multiple instances of the same module type.

## Key Features
- Singleton pattern implementation
- Multiple instance support
- Type-safe module retrieval
- Module lifecycle management
- Change notification system

## Class Structure

### ModuleManager
The main module management class that implements `ChangeNotifier`.

#### Properties
- `_log`: Static logger instance
- `_instance`: Static singleton instance
- `_modules`: Private map storing registered modules

#### Methods
- `registerModule`: Registers a new module instance
- `getModules`: Retrieves all instances of a module type
- `getModuleInstance`: Retrieves a specific module instance
- `getLatestModule`: Retrieves the latest instance of a module type
- `deregisterModule`: Removes a module instance
- `disposeModules`: Cleans up all modules

## Usage Examples

### Registering a Module
```dart
final moduleManager = ModuleManager();
moduleManager.registerModule(MyModule());
```

### Registering with Instance Key
```dart
moduleManager.registerModule(MyModule(), instanceKey: 'custom_key');
```

### Retrieving Modules
```dart
// Get all instances of a module type
final modules = ModuleManager().getModules<MyModule>('my_module_key');

// Get a specific instance
final module = ModuleManager().getModuleInstance<MyModule>('my_module_key', 'instance_key');

// Get the latest instance
final latestModule = ModuleManager().getLatestModule<MyModule>();
```

### Deregistering a Module
```dart
ModuleManager().deregisterModule('my_module_key', instanceKey: 'instance_key');
```

## Module Management Details

### Instance Management
- Supports multiple instances per module type
- Each instance can have a custom key
- Default key is the runtime type name
- Latest instance can be retrieved without a key

### Module Registration Process
1. Key generation/validation
2. Module storage
3. Listener notification
4. Logging

## Best Practices
1. Use meaningful module keys
2. Register modules before using them
3. Clean up modules when no longer needed
4. Use type-safe methods for retrieval
5. Handle module retrieval errors gracefully

## Error Handling
The ModuleManager includes:
- Module existence validation
- Type safety checks
- Comprehensive logging
- Graceful error recovery

## Dependencies
- `flutter/material.dart`
- `../../tools/logging/logger.dart`
- `../00_base/module_base.dart`

## Module Lifecycle
1. Registration
2. Usage
3. Deregistration
4. Cleanup

## Integration with Other Components
The ModuleManager works with:
- `ModuleBase`: Base class for all modules
- `ChangeNotifier`: State management
- `Logger`: Logging functionality

## Performance Considerations
- Modules are stored in memory
- Multiple instances are supported
- Instance lookup is optimized
- Large numbers of modules may impact performance

## State Management
The ModuleManager:
- Tracks module instances
- Notifies listeners of changes
- Manages module lifecycle
- Provides type-safe access 