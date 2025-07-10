# Services Manager Documentation

## Overview
The `ServicesManager` is a singleton class that manages application services. It provides a centralized system for registering, initializing, and accessing various services throughout the application lifecycle.

## Key Features
- Singleton pattern implementation
- Service registration and initialization
- Type-safe service retrieval
- Automatic service cleanup
- Change notification system

## Class Structure

### ServicesManager
The main service management class that implements `ChangeNotifier`.

#### Properties
- `_log`: Static logger instance
- `_instance`: Static singleton instance
- `_services`: Private map storing registered services

#### Methods
- `autoRegisterAllServices`: Registers default services
- `registerService`: Registers a new service
- `getService`: Retrieves a service with type safety
- `dispose`: Cleans up all registered services

## Usage Examples

### Registering a Service
```dart
final servicesManager = ServicesManager();
await servicesManager.registerService('my_service', MyService());
```

### Retrieving a Service
```dart
final service = ServicesManager().getService<MyService>('my_service');
```

### Auto-registering Default Services
```dart
await ServicesManager().autoRegisterAllServices();
```

## Service Registration Process
1. Service instance creation
2. Key validation
3. Service initialization
4. Storage in service map
5. Listener notification

## Built-in Services
The ServicesManager automatically registers:
- `SharedPrefManager`: For persistent storage

## Best Practices
1. Register services before using them
2. Use type-safe methods when retrieving services
3. Initialize services properly
4. Clean up services when they're no longer needed
5. Handle service retrieval errors gracefully

## Error Handling
The ServicesManager includes:
- Service existence validation
- Type safety checks
- Proper error logging
- Graceful error recovery

## Dependencies
- `flutter/material.dart`
- `../../tools/logging/logger.dart`
- `../00_base/service_base.dart`
- `../services/shared_preferences.dart`

## Service Lifecycle
1. Registration
2. Initialization
3. Usage
4. Cleanup

## Integration with Other Components
The ServicesManager works with:
- `ServicesBase`: Base class for all services
- `ChangeNotifier`: State management
- `Logger`: Logging functionality

## Service Types
The manager supports:
- Persistent storage services
- Network services
- Local storage services
- Custom services extending `ServicesBase` 