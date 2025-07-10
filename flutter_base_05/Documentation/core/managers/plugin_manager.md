# Plugin Manager Documentation

## Overview
The `PluginManager` is a core component that manages the lifecycle and registration of plugins in the application. It implements the `ChangeNotifier` pattern to notify listeners of plugin-related changes.

## Key Features
- Plugin registration and initialization
- Plugin lifecycle management
- Hook registration for plugins
- Type-safe plugin retrieval
- Automatic plugin cleanup

## Class Structure

### PluginManager
The main class that manages all plugins in the application.

#### Properties
- `_log`: Static logger instance
- `_plugins`: Private map storing registered plugins

#### Methods

##### Plugin Management
- `registerPlugin`: Registers and initializes a new plugin
- `deregisterPlugin`: Removes a specific plugin
- `getPlugin`: Retrieves a plugin instance with type safety
- `clearPlugins`: Removes all registered plugins
- `initializePlugins`: Initializes all required plugins for the application

##### Lifecycle Management
- `dispose`: Cleans up all plugins when the manager is disposed

## Usage Examples

### Registering a Plugin
```dart
final pluginManager = PluginManager();
pluginManager.registerPlugin(context, 'my_plugin', MyPlugin());
```

### Retrieving a Plugin
```dart
final plugin = pluginManager.getPlugin<MyPlugin>('my_plugin');
```

### Initializing All Plugins
```dart
await pluginManager.initializePlugins(context);
```

## Plugin Initialization Process
1. Plugin registration
2. Context initialization
3. Hook registration
4. State management setup
5. Notification of listeners

## Built-in Plugins
The PluginManager initializes three main plugins:
1. `MainPlugin`: Core application functionality
2. `GamePlugin`: Game-specific features
3. `AdvertsPlugin`: Advertisement management

## Hook System
The PluginManager automatically registers two hooks for each plugin:
1. `app_startup`: Triggered during application startup
2. `reg_nav`: Triggered during navigation registration

## Best Practices
1. Register plugins before using them
2. Use type-safe methods when retrieving plugins
3. Clean up plugins when they're no longer needed
4. Initialize plugins with the proper context
5. Handle plugin registration errors gracefully

## Error Handling
The PluginManager includes comprehensive error handling:
- Validates plugin registration
- Provides type safety checks
- Logs all plugin-related operations
- Handles plugin initialization errors

## Dependencies
- `flutter/material.dart`
- `provider/provider.dart`
- `../../plugins/adverts_plugin/adverts_plugin_main.dart`
- `../../plugins/game_plugin/game_plugin_main.dart`
- `../../plugins/main_plugin/main_plugin_main.dart`
- `../../tools/logging/logger.dart`
- `../00_base/plugin_base.dart`
- `hooks_manager.dart`
- `module_manager.dart`
- `state_manager.dart`

## Integration with Other Managers
The PluginManager works closely with:
- `HooksManager`: For plugin hook registration
- `StateManager`: For plugin state management
- `ModuleManager`: For plugin module management 