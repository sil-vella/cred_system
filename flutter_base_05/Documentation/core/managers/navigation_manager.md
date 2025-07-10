# Navigation Manager Documentation

## Overview
The `NavigationManager` is a singleton class that manages application navigation using the `go_router` package. It provides a centralized system for registering routes, managing drawer items, and creating the router configuration.

## Key Features
- Singleton pattern implementation
- Dynamic route registration
- Drawer item management
- Route priority system
- GoRouter integration
- Change notification system

## Classes

### RegisteredRoute
A class that represents a registered route in the application.

#### Properties
- `path`: The route path
- `screen`: The widget builder function for the route
- `drawerTitle`: Optional title for drawer item
- `drawerIcon`: Optional icon for drawer item
- `drawerPosition`: Position in the drawer (default: 999)

#### Methods
- `toGoRoute`: Converts the route to a GoRoute instance
- `shouldAppearInDrawer`: Checks if the route should appear in the drawer

### NavigationManager
The main navigation management class that implements `ChangeNotifier`.

#### Properties
- `_instance`: Static singleton instance
- `_routes`: Private list of registered routes

#### Methods
- `routes`: Getter for dynamically registered GoRoutes
- `drawerRoutes`: Getter for drawer-visible routes (sorted by position)
- `registerRoute`: Registers a new route
- `router`: Creates a GoRouter instance

## Usage Examples

### Registering a Route
```dart
final navManager = NavigationManager();
navManager.registerRoute(
  path: '/settings',
  screen: (context) => SettingsScreen(),
  drawerTitle: 'Settings',
  drawerIcon: Icons.settings,
  drawerPosition: 2
);
```

### Accessing Drawer Routes
```dart
final drawerItems = NavigationManager().drawerRoutes;
```

### Using the Router
```dart
final router = NavigationManager().router;
```

## Route Registration Process
1. Path validation
2. Duplicate checking
3. Route creation
4. Listener notification

## Drawer Management
The NavigationManager provides:
- Automatic drawer item sorting
- Position-based ordering
- Icon and title management
- Visibility control

## Best Practices
1. Use meaningful path names
2. Set appropriate drawer positions
3. Provide both drawer title and icon for drawer items
4. Register routes before using them
5. Use the router instance for navigation

## Error Handling
The NavigationManager includes:
- Duplicate route prevention
- Path validation
- Type safety for route parameters
- Proper error logging

## Dependencies
- `flutter/material.dart`
- `go_router/go_router.dart`
- `../../plugins/main_plugin/screens/home_screen.dart`

## Integration with Other Components
The NavigationManager works with:
- `HomeScreen`: Default route
- `GoRouter`: Navigation implementation
- `ChangeNotifier`: State management

## Route Priority System
Routes are prioritized in the drawer based on their `drawerPosition`:
- Lower numbers appear first
- Default position is 999 (lowest priority)
- Custom positions can be set during registration 