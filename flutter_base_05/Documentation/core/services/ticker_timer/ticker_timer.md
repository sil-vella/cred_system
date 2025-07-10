# Ticker Timer Service Documentation

## Overview
The `TickerTimer` service provides a flexible timer implementation using Flutter's `Ticker` class. It supports starting, pausing, resuming, and resetting timers, with proper state management and notifications.

## Key Features
- Multiple timer instances support
- Pause and resume functionality
- Elapsed time tracking
- State change notifications
- Automatic cleanup

## Class Structure

### TickerTimer
A service that extends `ServicesBase` and implements `ChangeNotifier`.

#### Properties
- `id`: Unique identifier for each timer instance
- `_ticker`: Private Ticker instance
- `_elapsedSeconds`: Current elapsed time
- `_isRunning`: Timer running state
- `_isPaused`: Timer paused state
- `_pausedDuration`: Duration when paused

#### Methods
- `initialize`: Initializes the timer service
- `startTimer`: Starts or resumes the timer
- `pauseTimer`: Pauses the timer
- `stopTimer`: Stops the timer
- `resetTimer`: Resets the timer to zero
- `dispose`: Cleans up resources

## Usage Examples

### Creating a Timer
```dart
final timer = TickerTimer(id: 'my_timer');
```

### Starting the Timer
```dart
timer.startTimer();
```

### Pausing the Timer
```dart
timer.pauseTimer();
```

### Stopping the Timer
```dart
timer.stopTimer();
```

### Resetting the Timer
```dart
timer.resetTimer();
```

## Timer Lifecycle
1. Initialization
2. Start/Resume
3. Pause (optional)
4. Stop
5. Reset (optional)

## State Management
- Tracks elapsed time
- Manages running state
- Handles pause state
- Notifies listeners of changes

## Best Practices
1. Use unique IDs for each timer
2. Properly dispose of timers
3. Handle state changes appropriately
4. Use notifications for UI updates
5. Clean up resources when done

## Error Handling
- Validates timer state
- Handles null cases
- Provides logging
- Graceful cleanup

## Dependencies
- `flutter/material.dart`
- `flutter/scheduler.dart`
- `../../tools/logging/logger.dart`
- `../00_base/service_base.dart`

## Integration Points
The TickerTimer integrates with:
- `ServicesManager`: For service registration
- `ChangeNotifier`: For state updates
- `Logger`: For logging operations

## Performance Considerations
- Efficient ticker usage
- Minimal rebuilds
- Proper resource cleanup
- State optimization 