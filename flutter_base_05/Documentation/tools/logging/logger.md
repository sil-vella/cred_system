# Logger Documentation

## Overview
The `Logger` class provides a centralized logging utility for the application, implementing a singleton pattern for consistent logging across the app. It offers various logging levels and respects the global logging configuration.

## Key Features
- Singleton pattern implementation
- Multiple logging levels
- Configurable logging output
- Stack trace support
- Forced logging capability

## Class Structure

### Logger
A singleton class that manages application logging.

#### Properties
- `_instance`: Static singleton instance

#### Methods
- `log`: General logging method
- `info`: Information level logging
- `debug`: Debug level logging
- `error`: Error level logging with stack trace support
- `forceLog`: Logging that bypasses configuration

## Usage Examples

### Basic Logging
```dart
final logger = Logger();
logger.info('Application started');
logger.debug('Processing data');
logger.error('An error occurred', error: exception, stackTrace: stackTrace);
```

### Forced Logging
```dart
logger.forceLog('Critical system message', 
  name: 'SystemLogger', 
  level: 1000
);
```

## Log Levels
- Info: 800
- Debug: 500
- Error: 1000
- Custom: 0-1000 range

## Configuration
- Controlled by `Config.loggerOn` flag
- Default logger name: 'AppLogger'
- Customizable log levels
- Optional stack trace inclusion

## Best Practices
1. Use appropriate log levels
2. Include relevant context
3. Handle stack traces
4. Respect logging configuration
5. Use meaningful logger names

## Error Handling
- Stack trace support
- Error object inclusion
- Level-based filtering
- Configuration validation

## Dependencies
- `dart:developer`
- `config.dart`

## Integration Points
The logger integrates with:
- Application configuration
- Debug tools
- Error handling
- Performance monitoring

## Performance Considerations
- Conditional logging
- Stack trace impact
- Memory usage
- Output formatting
- Configuration checks

## Security Considerations
- Sensitive data logging
- Stack trace exposure
- Log level control
- Force logging usage
- Configuration protection 