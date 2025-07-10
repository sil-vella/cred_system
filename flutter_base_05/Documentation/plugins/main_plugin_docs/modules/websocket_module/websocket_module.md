# WebSocket Module Documentation

## Overview
The `WebSocketModule` is a real-time communication module that handles WebSocket connections, room management, and event handling. It provides a robust framework for real-time data exchange and state synchronization.

## Key Features
- Real-time WebSocket communication
- Room management
- Session handling
- Token management
- Event handling
- Broadcast capabilities
- Message management
- State synchronization
- Unified room joining logic
- Async event handling

## Class Structure

### WebSocketModule
Extends `ModuleBase` and manages WebSocket functionality.

#### Properties
- `_moduleManager`: Module management instance
- `_servicesManager`: Service management instance
- `_stateManager`: State management instance
- `_sharedPref`: Shared preferences manager
- `_connectionModule`: API connection module
- `_currentContext`: Current build context
- `_mounted`: Module mount state

#### Components
- `_socketManager`: Manages socket connections
- `_roomManager`: Handles room operations
- `_sessionManager`: Manages user sessions
- `_tokenManager`: Handles authentication tokens
- `_eventHandler`: Processes socket events
- `_resultHandler`: Manages operation results
- `_broadcastManager`: Handles broadcasts
- `_messageManager`: Manages messages

## Connection Management

### Connection Process
1. Token validation
2. Socket connection
3. Session initialization
4. State synchronization
5. Event handler setup
6. Room state initialization

### Disconnection Process
1. Room cleanup
2. Socket disconnection
3. Session cleanup
4. State reset
5. Resource cleanup
6. Event handler cleanup

## Event Handling

### Core Events
- `connect`: Connection established
- `disconnect`: Connection terminated
- `session_update`: Session data changes
- `room_joined`: Room join success
- `room_state`: Room state updates
- `error`: Error notifications

### Event State Management
```dart
// Example of state updates for different events
switch (event) {
  case 'connect':
    // Update connection state
    break;
  case 'disconnect':
    // Reset connection and room state
    break;
  case 'session_update':
    // Update session data
    break;
  case 'room_joined':
    // Update room membership
    break;
  case 'room_state':
    // Update room state
    break;
  case 'error':
    // Handle error state
    break;
}
```

## Usage Examples

### Connecting to WebSocket
```dart
final success = await webSocketModule.connect(context);
if (success) {
  // Connection successful
}
```

### Joining a Room
```dart
final result = await webSocketModule.roomManager.joinRoom(roomId);
// Handle room state updates
webSocketModule.eventHandler.eventStream.listen((event) {
  if (event['event'] == 'room_joined') {
    // Handle room join success
  } else if (event['event'] == 'room_state') {
    // Handle room state updates
  }
});
```

### Sending a Message
```dart
await webSocketModule.messageManager.sendMessage(
  roomId: roomId,
  message: message,
);
```

## State Management
- Connection status
- Session data
- Room state
- User information
- Error states
- Loading states
- Room membership
- Event history

## Event Handling
- Connection events
- Room events
- Message events
- Error events
- State change events
- Room state events
- Session events

## Security Features
- Token validation
- Session management
- Connection security
- Message validation
- Room access control
- Event validation

## Error Handling
- Connection errors
- Authentication errors
- Room operation errors
- Message handling errors
- State synchronization errors
- Event handling errors
- Room state errors

## Dependencies
- `socket_io_client`
- `flutter/material.dart`
- `provider` package
- `SharedPrefManager`
- `ConnectionsApiModule`
- `StateManager`

## Integration Points
The WebSocketModule integrates with:
- `ModuleManager`: For module access
- `ServicesManager`: For service access
- `StateManager`: For state updates
- `SharedPrefManager`: For data persistence
- `ConnectionsApiModule`: For API communication
- `LoginModule`: For user authentication

## Best Practices
1. Proper connection management
2. Efficient room handling
3. Secure token management
4. Robust error handling
5. State synchronization
6. Event handler registration
7. Room state management
8. Session state tracking
9. Error state handling
10. Async operation management

## Performance Considerations
- Connection optimization
- Message batching
- State update efficiency
- Resource management
- Memory usage
- Event handler efficiency
- Room state updates
- Session state management

## Security Considerations
- Token security
- Session validation
- Message encryption
- Connection security
- Access control
- Event validation
- Room access control
- State security 