# Function Helper Module Documentation

## Overview
The `FunctionHelperModule` is a utility module that provides helper functions for game-related operations, including points management, image caching, and user progress handling. It extends `ModuleBase` and offers various utility methods for game functionality.

## Key Features
- Points calculation and management
- Image cache management
- User progress handling
- SharedPreferences integration
- Data cleanup utilities

## Class Structure

### FunctionHelperModule
Extends `ModuleBase` and provides game utility functions.

#### Properties
- `_log`: Logger instance

#### Methods
- `getTotalPoints`: Calculates total points across categories
- `storeImageCacheTimestamp`: Manages image cache timestamps
- `cleanupExpiredImages`: Removes expired image cache entries
- `clearUserProgress`: Resets user progress data

## Usage Examples

### Getting Total Points
```dart
final functionHelper = FunctionHelperModule();
int totalPoints = await functionHelper.getTotalPoints(context);
```

### Managing Image Cache
```dart
// Store image cache timestamp
await functionHelper.storeImageCacheTimestamp(context, imageUrl);

// Clean up expired images
await functionHelper.cleanupExpiredImages(context);
```

### Clearing User Progress
```dart
await functionHelper.clearUserProgress(context);
```

## Data Management
- Points tracking across categories
- Image cache expiration (60 days)
- User progress persistence
- SharedPreferences integration
- Data cleanup mechanisms

## Best Practices
1. Regular cache cleanup
2. Proper error handling
3. Data validation
4. Progress backup
5. Resource management

## Error Handling
- SharedPreferences errors
- Data parsing errors
- Cache management errors
- Progress reset errors
- Service availability errors

## Dependencies
- `flutter/material.dart`
- `provider` package
- `Logger`
- `SharedPrefManager`
- `ServicesManager`

## Integration Points
The module integrates with:
- `SharedPrefManager`: For data persistence
- `ServicesManager`: For service access
- `ModuleManager`: For module access
- `MainHelperModule`: For utility functions

## Performance Considerations
- Cache optimization
- Data cleanup efficiency
- Memory management
- Storage usage
- Resource cleanup

## Security Considerations
- Data integrity
- Progress protection
- Cache security
- Error message handling
- Service access control 