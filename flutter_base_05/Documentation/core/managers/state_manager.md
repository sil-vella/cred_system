# State Manager Documentation

## Overview
The `StateManager` is a singleton class that manages the application's state using the Provider pattern. It handles both plugin-specific states and the main application state, providing a centralized state management solution.

## Key Features
- Singleton pattern implementation
- Plugin state management
- Main application state management
- Type-safe state access
- State merging capabilities
- Change notification system

## Classes

### PluginState
A class that represents the state of a plugin.

#### Properties
- `state`: A `Map<String, dynamic>` containing the plugin's state data

#### Methods
- `fromDynamic`: Factory constructor that converts a dynamic map to a properly typed state
- `merge`: Merges new state with existing state

### StateManager
The main state management class that implements `ChangeNotifier`.

#### Properties
- `_pluginStates`: Private map storing plugin states
- `_mainAppState`: Private map storing main application state
- `_instance`: Static singleton instance
- `_log`: Static logger instance

#### Methods

##### Plugin State Management
- `isPluginStateRegistered`: Checks if a plugin state is registered
- `registerPluginState`: Registers a new plugin state
- `unregisterPluginState`: Removes a plugin state
- `getPluginState`: Retrieves a plugin state with type safety
- `updatePluginState`: Updates an existing plugin state
- `getAllPluginStates`: Returns all registered plugin states
- `getRegisteredPluginKeys`: Returns list of all registered plugin keys
- `getPluginStateCount`: Returns the number of registered plugin states
- `hasPluginStates`: Checks if any plugin states are registered

##### Main App State Management
- `setMainAppState`: Initializes the main application state
- `updateMainAppState`: Updates a specific key in the main application state
- `getMainAppState`: Retrieves a value from the main application state with type safety

## Usage Examples

### Registering a Plugin State
```dart
final stateManager = StateManager();
stateManager.registerPluginState('myPlugin', {
  'isActive': true,
  'counter': 0
});
```

### Updating Plugin State
```dart
stateManager.updatePluginState('myPlugin', {
  'counter': 1
});
```

### Accessing Plugin State
```dart
final state = stateManager.getPluginState<Map<String, dynamic>>('myPlugin');
```

### Managing Main App State
```dart
// Set initial state
stateManager.setMainAppState({
  'theme': 'dark',
  'language': 'en'
});

// Update state
stateManager.updateMainAppState('theme', 'light');

// Get state
final theme = stateManager.getMainAppState<String>('theme');
```

## Best Practices
1. Always register plugin states before using them
2. Use type-safe methods when accessing state
3. Update state through the manager rather than directly
4. Handle null cases when retrieving state
5. Use the merge functionality for partial state updates

## Error Handling
The StateManager includes comprehensive error handling and logging:
- Validates state registration before updates
- Provides type safety checks
- Logs all state changes and errors
- Handles null cases gracefully

## Dependencies
- `flutter/foundation.dart`
- `flutter/material.dart`
- `../../tools/logging/logger.dart` 