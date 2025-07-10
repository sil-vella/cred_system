# Connection Status Component Documentation

## Overview
The `ConnectionStatus` component provides a visual representation of the WebSocket connection state and room information. It includes connection controls and displays the current room ID when connected. The component updates in real-time through the `StateManager`.

## Key Features
- Connection state display
- Connection controls
- Room information display
- Real-time updates
- Visual status indicators

## Component Structure

### ConnectionStatus
A `StatelessWidget` that displays connection status and controls.

#### Properties
- `key`: Widget key
- `onConnect`: Callback for connect action
- `onDisconnect`: Callback for disconnect action

#### Methods
- `build`: Builds the component UI

## UI Elements
- Connection Status Indicator
  - WiFi icon (connected/disconnected)
  - Status text
  - Color-coded indicators
- Connection Controls
  - Connect button (when disconnected)
  - Disconnect button (when connected)
- Room Information
  - Room ID display
  - Room icon

## Usage Examples

### Basic Implementation
```dart
ConnectionStatus(
  onConnect: () => _connectToWebSocket(),
  onDisconnect: () => _disconnectFromWebSocket(),
);
```

### State Management
```dart
Consumer<StateManager>(
  builder: (context, stateManager, child) {
    final gameRoomState = stateManager.getPluginState<Map<String, dynamic>>("game_room") ?? {};
    final isConnected = gameRoomState['isConnected'] ?? false;
    // ... use state
  },
);
```

## State Management
- Uses `StateManager` for state access
- Consumes game room state
- Updates in real-time
- Handles null states
- Provides default values

## Best Practices
1. Clear status indication
2. Consistent button styling
3. Proper callback handling
4. State validation
5. UI responsiveness

## Error Handling
- Null state handling
- Missing data handling
- State validation
- UI overflow handling
- Callback validation

## Dependencies
- `flutter/material.dart`
- `provider` package
- `StateManager`

## Integration Points
The component integrates with:
- `StateManager`: For state access
- `GameScreen`: For parent context
- `Theme`: For styling

## Performance Considerations
- Efficient state updates
- Minimal rebuilds
- Optimized layout
- Memory usage
- UI rendering

## UI/UX Considerations
- Clear status indicators
- Intuitive controls
- Responsive layout
- Text overflow handling
- Consistent spacing
- Color-coded feedback
- Icon usage 