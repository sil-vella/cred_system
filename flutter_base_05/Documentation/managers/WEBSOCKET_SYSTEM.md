# Flutter WebSocket System Documentation

## 🎯 Overview

The Flutter WebSocket System provides a robust, centralized architecture for real-time communication between the Flutter app and the backend server. It uses Socket.IO for reliable WebSocket connections with automatic reconnection, JWT authentication, and comprehensive event management.

## 🏗️ Architecture

### **Core Components**

```
┌─────────────────────────────────────────────────────────────┐
│                    Flutter App                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────┐   │
│  │   WebSocket     │    │      WSEventManager         │   │
│  │   Manager       │◄──►│   (Event Orchestrator)      │   │
│  │  (Connection)   │    │                             │   │
│  └─────────────────┘    └─────────────────────────────┘   │
│           │                        │                      │
│           ▼                        ▼                      │
│  ┌─────────────────┐    ┌─────────────────────────────┐   │
│  │   Socket.IO     │    │      StateManager           │   │
│  │   Client        │    │   (State Management)        │   │
│  └─────────────────┘    └─────────────────────────────┘   │
│           │                        │                      │
│           ▼                        ▼                      │
│  ┌─────────────────┐    ┌─────────────────────────────┐   │
│  │   AuthManager   │    │      Modules                │   │
│  │ (JWT Tokens)    │    │   (Event Listeners)        │   │
│  └─────────────────┘    └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### **Data Flow**

1. **Connection**: WebSocketManager establishes Socket.IO connection with JWT authentication
2. **Event Reception**: Incoming events are processed by WSEventManager
3. **Event Distribution**: Events are distributed to registered listeners via callbacks
4. **State Updates**: StateManager is updated with current connection and room state
5. **UI Updates**: Modules and screens receive events and update their UI accordingly

## 🔧 Core Managers

### **1. WebSocketManager**

**Purpose**: Handles the low-level Socket.IO connection, authentication, and connection state management.

**Key Features**:
- Singleton pattern for global access
- JWT token-based authentication
- Automatic reconnection handling
- Connection state tracking
- Event stream management

**Key Methods**:
```dart
// Initialize WebSocket connection
Future<bool> initialize() async

// Check connection status
bool get isConnected

// Get event manager
WSEventManager get eventManager

// Send message to room
Future<Map<String, dynamic>> sendMessage(String roomId, String message)

// Join room
Future<Map<String, dynamic>> joinRoom(String roomId)

// Leave room
Future<Map<String, dynamic>> leaveRoom(String roomId)
```

**Configuration**:
```dart
// Socket.IO configuration
_socket = IO.io(Config.wsUrl, <String, dynamic>{
  'transports': ['websocket'],
  'autoConnect': false,
  'query': {
    'token': authToken,
    'client_id': 'flutter_app_${DateTime.now().millisecondsSinceEpoch}',
    'version': '1.0.0',
  },
  'auth': {
    'token': authToken,
  },
});
```

### **2. WSEventManager**

**Purpose**: Centralized event handling and distribution system that processes all WebSocket events and distributes them to registered listeners.

**Key Features**:
- Event type classification and routing
- Callback registration system
- State synchronization with StateManager
- Error handling and logging
- Custom event support

**Event Types**:
- `'room'` - Room events (joined, left, created)
- `'message'` - Message events
- `'connection'` - Connection status events
- `'session'` - Session data events
- `'error'` - Error events
- `'custom_event_name'` - Custom events

**Key Methods**:
```dart
// Register event listener
void onEvent(String eventType, Function(Map<String, dynamic>) callback)

// Unregister event listener
void offEvent(String eventType, Function(Map<String, dynamic>) callback)

// Register one-time event listener
void onceEvent(String eventType, Function(Map<String, dynamic>) callback)

// Clear all callbacks
void clearCallbacks()
```

### **3. StateManager Integration**

**Purpose**: Maintains centralized state for WebSocket connection, rooms, and session data.

**State Structure**:
```dart
{
  "websocket": {
    "isConnected": bool,
    "currentRoomId": String?,
    "currentRoomInfo": Map<String, dynamic>?,
    "sessionData": Map<String, dynamic>?
  }
}
```

## 📡 Event System

### **Event Flow**

```
Backend Server
     │
     ▼
Socket.IO Client (WebSocketManager)
     │
     ▼
Event Streams (WSEventManager)
     │
     ▼
Event Callbacks (Modules/Screens)
     │
     ▼
UI Updates (StateManager)
```

### **Event Types and Data**

#### **Connection Events**
```dart
{
  'status': 'connected' | 'disconnected' | 'connecting' | 'error',
  'sessionId': String?,
  'error': String?
}
```

#### **Room Events**
```dart
{
  'action': 'joined' | 'left' | 'created',
  'roomId': String,
  'roomData': Map<String, dynamic>
}
```

#### **Message Events**
```dart
{
  'roomId': String,
  'message': String,
  'sender': String,
  'additionalData': Map<String, dynamic>?
}
```

#### **Error Events**
```dart
{
  'error': String,
  'details': String?
}
```

#### **Custom Events**
```dart
{
  'eventName': String,
  'data': Map<String, dynamic>
}
```

## 🔐 Authentication

### **JWT Token Management**

The WebSocket system uses JWT tokens for authentication:

1. **Token Retrieval**: WebSocketManager gets JWT token from LoginModule
2. **Token Validation**: Checks token validity before connection
3. **Token Refresh**: Automatic token refresh every 4 minutes
4. **Secure Storage**: Tokens stored in FlutterSecureStorage

```dart
// Token retrieval from LoginModule
final authToken = await loginModule.getCurrentToken();

// Token validation
final hasToken = await loginModule.hasValidToken();
```

### **Connection Authentication**

```dart
// Socket.IO connection with JWT authentication
_socket = IO.io(Config.wsUrl, <String, dynamic>{
  'transports': ['websocket'],
  'autoConnect': false,
  'query': {
    'token': authToken,
    'client_id': 'flutter_app_${DateTime.now().millisecondsSinceEpoch}',
    'version': '1.0.0',
  },
  'auth': {
    'token': authToken,
  },
});
```

## 🧩 Module Integration

### **Registering Event Listeners in Modules**

Modules can register WebSocket event listeners during initialization:

```dart
class ChatModule extends ModuleBase {
  static final Logger _log = Logger();
  late WSEventManager _wsEventManager;

  ChatModule() : super("chat_module", dependencies: ["connections_api_module"]);

  @override
  void initialize(BuildContext context, ModuleManager moduleManager) {
    super.initialize(context, moduleManager);
    
    // Get WSEventManager instance
    _wsEventManager = WSEventManager.instance;
    
    // Register WebSocket listeners
    _registerWebSocketListeners();
    
    _log.info('✅ ChatModule initialized with WebSocket listeners');
  }

  void _registerWebSocketListeners() {
    // Listen for room events
    _wsEventManager.onEvent('room', _handleRoomEvent);
    
    // Listen for messages
    _wsEventManager.onEvent('message', _handleMessageEvent);
    
    // Listen for connection status
    _wsEventManager.onEvent('connection', _handleConnectionEvent);
    
    // Listen for errors
    _wsEventManager.onEvent('error', _handleErrorEvent);
    
    // Listen for custom events
    _wsEventManager.onEvent('user_typing', _handleUserTyping);
  }

  void _handleRoomEvent(Map<String, dynamic> data) {
    final action = data['action'];
    final roomId = data['roomId'];
    
    _log.info("📨 Chat room event: action=$action, roomId=$roomId");
    
    // Update chat state based on room events
    _updateChatState(action, roomId, data);
  }

  void _handleMessageEvent(Map<String, dynamic> data) {
    final roomId = data['roomId'];
    final message = data['message'];
    final sender = data['sender'];
    
    _log.info("💬 Chat message in room $roomId from $sender: $message");
    
    // Add message to chat history
    _addMessageToHistory(roomId, message, sender);
  }

  void _handleConnectionEvent(Map<String, dynamic> data) {
    final status = data['status'];
    
    _log.info("🔌 Chat connection status: $status");
    
    if (status == 'connected') {
      _onChatConnected();
    } else if (status == 'disconnected') {
      _onChatDisconnected();
    }
  }

  void _handleErrorEvent(Map<String, dynamic> data) {
    final error = data['error'];
    _log.error("🚨 Chat WebSocket error: $error");
    _handleChatError(error);
  }

  void _handleUserTyping(Map<String, dynamic> data) {
    final userId = data['userId'];
    final roomId = data['roomId'];
    _log.info("⌨️ User $userId is typing in room $roomId");
    _updateTypingIndicator(userId, roomId, true);
  }

  @override
  void dispose() {
    // Remove all event listeners
    _wsEventManager.offEvent('room', _handleRoomEvent);
    _wsEventManager.offEvent('message', _handleMessageEvent);
    _wsEventManager.offEvent('connection', _handleConnectionEvent);
    _wsEventManager.offEvent('error', _handleErrorEvent);
    _wsEventManager.offEvent('user_tying', _handleUserTyping);
    
    _log.info('🗑️ ChatModule disposed - WebSocket listeners removed');
    super.dispose();
  }
}
```

### **Screen Integration**

Screens can also register event listeners for UI updates:

```dart
class RoomManagementScreen extends StatefulWidget {
  @override
  _RoomManagementScreenState createState() => _RoomManagementScreenState();
}

class _RoomManagementScreenState extends State<RoomManagementScreen> {
  final WSEventManager _wsEventManager = WSEventManager.instance;
  final Logger log = Logger();

  @override
  void initState() {
    super.initState();
    _setupEventCallbacks();
  }

  void _setupEventCallbacks() {
    // Listen for room events
    _wsEventManager.onEvent('room', (data) {
      final action = data['action'];
      final roomId = data['roomId'];
      
      log.info("📨 Received room event: action=$action, roomId=$roomId");
      
      if (action == 'joined') {
        _showSnackBar('Successfully joined room: $roomId');
      } else if (action == 'left') {
        _showSnackBar('Left room: $roomId');
      } else if (action == 'created') {
        _showSnackBar('Room created: $roomId');
      }
    });

    // Listen for error events
    _wsEventManager.onEvent('error', (data) {
      final error = data['error'];
      _showSnackBar('Error: $error', isError: true);
    });
  }

  @override
  void dispose() {
    // Clean up listeners
    _wsEventManager.offEvent('room', _handleRoomEvent);
    _wsEventManager.offEvent('error', _handleErrorEvent);
    super.dispose();
  }
}
```

## 🔄 Connection Lifecycle

### **1. Initialization**
```dart
// Initialize WebSocket manager
final wsManager = WebSocketManager.instance;
await wsManager.initialize();
```

### **2. Connection Process**
1. **Token Validation**: Check JWT token availability
2. **Socket Creation**: Create Socket.IO client with authentication
3. **Event Handler Setup**: Register event handlers
4. **Connection Attempt**: Connect to WebSocket server
5. **State Update**: Update connection state in StateManager

### **3. Event Handling**
1. **Event Reception**: Socket.IO receives events from server
2. **Event Processing**: WSEventManager processes and categorizes events
3. **Callback Execution**: Registered callbacks are executed
4. **State Update**: StateManager is updated with new state
5. **UI Update**: UI components receive state updates

### **4. Disconnection**
1. **Manual Disconnect**: User or app initiates disconnect
2. **Automatic Reconnect**: Socket.IO attempts automatic reconnection
3. **State Cleanup**: Clean up connection state
4. **Event Cleanup**: Remove event listeners

## 🛠️ Usage Examples

### **Basic Connection**
```dart
// Initialize WebSocket connection
final wsManager = WebSocketManager.instance;
final success = await wsManager.initialize();

if (success) {
  print('✅ WebSocket connected successfully');
} else {
  print('❌ WebSocket connection failed');
}
```

### **Sending Messages**
```dart
// Send message to room
final wsManager = WebSocketManager.instance;
final result = await wsManager.sendMessage('room_123', 'Hello, world!');

if (result['success'] != null) {
  print('✅ Message sent successfully');
} else {
  print('❌ Failed to send message: ${result['error']}');
}
```

### **Joining Rooms**
```dart
// Join a room
final wsManager = WebSocketManager.instance;
final result = await wsManager.joinRoom('room_123');

if (result['success'] != null) {
  print('✅ Joined room successfully');
} else {
  print('❌ Failed to join room: ${result['error']}');
}
```

### **Event Listening**
```dart
// Register event listener
final wsEventManager = WSEventManager.instance;

wsEventManager.onEvent('message', (data) {
  final roomId = data['roomId'];
  final message = data['message'];
  final sender = data['sender'];
  
  print('💬 Message from $sender in room $roomId: $message');
});

// Register one-time listener
wsEventManager.onceEvent('connection', (data) {
  final status = data['status'];
  print('🔌 Connection status: $status');
});
```

## 🔧 Configuration

### **WebSocket URL Configuration**
```dart
// In config.dart
class Config {
  static const String wsUrl = 'ws://your-server.com:3000';
  // or for production
  // static const String wsUrl = 'wss://your-server.com';
}
```

### **Socket.IO Options**
```dart
// Default Socket.IO configuration
{
  'transports': ['websocket'],
  'autoConnect': false,
  'query': {
    'token': authToken,
    'client_id': 'flutter_app_${DateTime.now().millisecondsSinceEpoch}',
    'version': '1.0.0',
  },
  'auth': {
    'token': authToken,
  },
}
```

## 🐛 Debugging

### **Connection Issues**
1. **Check JWT Token**: Ensure valid token is available
2. **Check Network**: Verify network connectivity
3. **Check Server**: Ensure WebSocket server is running
4. **Check Logs**: Review connection logs for errors

### **Event Issues**
1. **Check Event Registration**: Verify event listeners are registered
2. **Check Event Names**: Ensure event names match between client and server
3. **Check Callbacks**: Verify callback functions are properly defined
4. **Check State**: Review StateManager state for inconsistencies

### **Common Error Messages**
- `"No valid JWT token available"` - Authentication issue
- `"WebSocket connection error"` - Network or server issue
- `"Event callback error"` - Callback function error
- `"Socket not initialized"` - Initialization issue

## 📊 Monitoring

### **Connection Status**
```dart
// Check connection status
final wsManager = WebSocketManager.instance;
final isConnected = wsManager.isConnected;
final isConnecting = wsManager.isConnecting;

print('Connected: $isConnected, Connecting: $isConnecting');
```

### **Event Statistics**
```dart
// Get event manager statistics
final wsEventManager = WSEventManager.instance;
final currentRoomId = wsEventManager.currentRoomId;
final currentRoomInfo = wsEventManager.currentRoomInfo;
final sessionData = wsEventManager.sessionData;
final isConnected = wsEventManager.isConnected;

print('Current Room: $currentRoomId');
print('Connected: $isConnected');
```

## 🔒 Security Considerations

### **JWT Token Security**
- Tokens are stored securely using FlutterSecureStorage
- Automatic token refresh prevents expiration
- Token validation before connection
- Secure transmission over WebSocket

### **Event Validation**
- Server-side event validation
- Client-side event type checking
- Error handling for malformed events
- Rate limiting on server side

### **Connection Security**
- WebSocket over TLS (WSS) in production
- Authentication required for all connections
- Session management and cleanup
- Automatic reconnection with authentication

## 🚀 Best Practices

### **1. Event Listener Management**
- Always register listeners in `initialize()` method
- Always remove listeners in `dispose()` method
- Use descriptive callback function names
- Handle errors gracefully in callbacks

### **2. State Management**
- Use StateManager for centralized state
- Update state in event callbacks
- Avoid direct state manipulation
- Keep state consistent across components

### **3. Error Handling**
- Implement comprehensive error handling
- Log errors for debugging
- Provide user-friendly error messages
- Handle connection failures gracefully

### **4. Performance**
- Use efficient event handling
- Avoid blocking operations in callbacks
- Clean up resources properly
- Monitor memory usage

### **5. Testing**
- Test connection scenarios
- Test event handling
- Test error conditions
- Test reconnection logic

## 📚 Related Documentation

- [Module System Documentation](../modules/MODULE_SYSTEM.md)
- [State Manager Documentation](./STATE_MANAGER.md)
- [Authentication System Documentation](./AUTH_SYSTEM.md)
- [Event System Documentation](./EVENT_SYSTEM.md)

## 🔄 Version History

- **v1.0.0**: Initial WebSocket system implementation
- **v1.1.0**: Added WSEventManager for centralized event handling
- **v1.2.0**: Integrated with StateManager for state management
- **v1.3.0**: Added JWT authentication and token refresh
- **v1.4.0**: Improved error handling and reconnection logic
- **v1.5.0**: Added comprehensive module integration support

---

*This documentation covers the complete Flutter WebSocket system implementation. For questions or issues, refer to the codebase or contact the development team.* 