# App Manager Documentation

## Overview
The `AppManager` is a singleton class that manages the overall application lifecycle and initialization. It coordinates the initialization of plugins and provides global application state management.

## Key Features
- Singleton pattern implementation
- Application initialization management
- Plugin initialization coordination
- Global context management
- State tracking
- Change notification system

## Class Structure

### AppManager
The main application management class that implements `ChangeNotifier`.

#### Properties
- `_log`: Static logger instance
- `_instance`: Static singleton instance
- `globalContext`: Static global build context
- `_isInitialized`: Private initialization state flag
- `_hooksManager`: Instance of HooksManager

#### Methods
- `initializeApp`: Initializes the application
- `_initializePlugins`: Private method for plugin initialization

## Usage Examples

### Initializing the Application
```dart
final appManager = AppManager();
await appManager.initializeApp(context);
```

### Checking Initialization Status
```dart
if (AppManager().isInitialized) {
  // Application is ready
}
```

## Initialization Process
1. Context validation
2. Navigation setup
3. Plugin initialization
4. State update
5. Listener notification

## Integration Points
The AppManager coordinates with:
- `PluginManager`: For plugin initialization
- `HooksManager`: For hook management
- `GoRouter`: For navigation
- `Provider`: For state management

## Best Practices
1. Initialize the app only once
2. Use the global context carefully
3. Check initialization status before operations
4. Handle initialization errors gracefully
5. Use proper navigation methods

## Error Handling
The AppManager includes:
- Initialization state tracking
- Context validation
- Proper error logging
- Graceful error recovery

## Dependencies
- `flutter/material.dart`
- `provider/provider.dart`
- `go_router/go_router.dart`
- `../../tools/logging/logger.dart`
- `hooks_manager.dart`
- `plugin_manager.dart`

## Application Lifecycle
1. Initialization
2. Plugin setup
3. Navigation setup
4. State management
5. Cleanup

## Global Context Usage
The `globalContext` property:
- Provides access to the application context
- Should be used carefully
- Is set during initialization
- Can be accessed globally

## State Management
The AppManager:
- Tracks initialization state
- Notifies listeners of changes
- Manages plugin states
- Coordinates with other managers 