import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:provider/provider.dart';
import '../../tools/logging/logger.dart';
import '../managers/state_manager.dart';
import '../../utils/consts/config.dart';
import '../../modules/login_module/login_module.dart';
import '../managers/module_manager.dart';
import 'dart:async';
import 'dart:convert';

class WebSocketManager {
  static final WebSocketManager _instance = WebSocketManager._internal();
  factory WebSocketManager() => _instance;
  WebSocketManager._internal();

  static final Logger _log = Logger();
  
  IO.Socket? _socket;
  bool _isInitialized = false;
  bool _isConnected = false;
  String? _sessionId;
  String? _userId;
  String? _username;
  String? _currentRoomId;
  
  // Event handling
  final StreamController<Map<String, dynamic>> _eventStreamController = StreamController<Map<String, dynamic>>.broadcast();
  final Map<String, Function(Map<String, dynamic>)> _eventHandlers = {};
  
  // Room management
  final Map<String, Set<String>> _rooms = {};
  final Map<String, Set<String>> _sessionRooms = {};
  
  // Token management
  Timer? _tokenRefreshTimer;
  
  // State management
  Map<String, dynamic>? _pendingStateUpdate;
  
  // Module manager for accessing LoginModule
  final ModuleManager _moduleManager = ModuleManager();

  // Getters
  IO.Socket? get socket => _socket;
  bool get isConnected => _isConnected;
  bool get isInitialized => _isInitialized;
  String? get sessionId => _sessionId;
  String? get userId => _userId;
  String? get username => _username;
  String? get currentRoomId => _currentRoomId;
  Stream<Map<String, dynamic>> get eventStream => _eventStreamController.stream;

  /// Initialize the WebSocket manager
  Future<bool> initialize(BuildContext context) async {
    if (_isInitialized) {
      _log.info("✅ WebSocket manager already initialized");
      return _isConnected;
    }

    try {
      _log.info("🔄 Initializing WebSocket manager...");
      
      // Register websocket state in StateManager if not already registered
      final stateManager = Provider.of<StateManager>(context, listen: false);
      if (!stateManager.isPluginStateRegistered("websocket")) {
        stateManager.registerPluginState("websocket", {
          'isConnected': false,
          'sessionId': null,
          'userId': null,
          'username': null,
          'currentRoomId': null,
          'roomState': null,
          'error': null,
          'connectionTime': null,
          'lastActivity': null,
        });
        _log.info("✅ Registered websocket state in StateManager");
      }
      
      // Check if we already have a connection from StateManager
      final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
      
      if (websocketState != null && websocketState['isConnected'] == true) {
        _log.info("✅ Using existing WebSocket connection from StateManager");
        _isInitialized = true;
        _isConnected = true;
        _updateConnectionInfo(context);
        return true;
      }
      
      // Get JWT token from login module for authentication
      final loginModule = _moduleManager.getModuleByType<LoginModule>();
      if (loginModule == null) {
        _log.error("❌ Login module not available for WebSocket authentication");
        return false;
      }
      
      // Check if user has valid JWT token
      final hasToken = await loginModule.hasValidToken();
      if (!hasToken) {
        _log.error("❌ No valid JWT token available for WebSocket authentication");
        return false;
      }
      
      // Get the JWT token
      final authToken = await loginModule.getCurrentToken();
      if (authToken == null) {
        _log.error("❌ Failed to retrieve JWT token for WebSocket authentication");
        return false;
      }
      
      _log.info("✅ Using JWT token for WebSocket authentication");
      
      // Create Socket.IO connection
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

      // Set up event listeners
      _setupEventHandlers();
      
      // Start token refresh timer
      _startTokenRefreshTimer();
      
      _isInitialized = true;
      _log.info("✅ WebSocket manager initialized successfully");
      return true;
      
    } catch (e) {
      _log.error("❌ Error initializing WebSocket manager: $e");
      return false;
    }
  }

  /// Set up Socket.IO event handlers
  void _setupEventHandlers() {
    if (_socket == null) return;
    
    _socket!.onConnect((_) {
      _log.info("✅ WebSocket connected successfully");
      _isConnected = true;
      _sessionId = _socket!.id;
      _log.info("✅ Session ID: ${_socket!.id}");
      _handleEvent('connect', {});
    });

    _socket!.onDisconnect((_) {
      _log.info("❌ WebSocket disconnected");
      _isConnected = false;
      _sessionId = null;
      _currentRoomId = null;
      _handleEvent('disconnect', {});
    });

    _socket!.onConnectError((error) {
      _log.error("🚨 WebSocket connection error: $error");
      _isConnected = false;
      _sessionId = null;
      _handleEvent('error', {'error': error.toString()});
    });

    _socket!.on('session_data', (data) {
      _log.info("📋 Received session data from WebSocket server");
      // Update connection info from session data
      if (data is Map<String, dynamic>) {
        _userId = data['userId'];
        _username = data['username'];
      }
      _handleEvent('session_update', data);
    });

    _socket!.on('join_room_success', (data) {
      _log.info("🏠 Successfully joined room");
      _handleEvent('room_joined', data);
    });

    _socket!.on('join_room_error', (data) {
      _log.error("🚨 Failed to join room: $data");
      _handleEvent('join_room_error', data);
    });

    _socket!.on('create_room_success', (data) {
      _log.info("🏠 Successfully created room");
      _handleEvent('create_room_success', data);
    });

    _socket!.on('create_room_error', (data) {
      _log.error("🚨 Failed to create room: $data");
      _handleEvent('create_room_error', data);
    });

    _socket!.on('message', (data) {
      _log.info("💬 Received message: $data");
      _handleEvent('message', data);
    });

    _socket!.on('error', (data) {
      _log.error("🚨 WebSocket error: $data");
      _handleEvent('error', data);
    });

    // Register custom event handlers
    _eventHandlers.forEach((event, handler) {
      _socket!.on(event, (data) {
        _log.info("📨 Received custom event '$event': $data");
        _handleEvent(event, data);
      });
    });
  }

  /// Handle events and broadcast to stream
  void _handleEvent(String event, Map<String, dynamic> data) {
    // Add event type to data
    final eventData = {
      'event': event,
      ...data
    };

    // Update StateManager based on event type
    switch (event) {
      case 'connect':
        _updateStateManager({
          'isConnected': true,
          'sessionId': _sessionId,
          'connectionTime': DateTime.now().toIso8601String(),
          'error': null
        });
        break;
      case 'disconnect':
        _updateStateManager({
          'isConnected': false,
          'sessionId': null,
          'currentRoomId': null,
          'roomState': null,
          'error': null
        });
        break;
      case 'session_update':
        _updateStateManager({
          'sessionData': data['session_data'],
          'userId': data['user_id'],
          'username': data['username'],
          'lastActivity': DateTime.now().toIso8601String(),
          'error': null
        });
        break;
      case 'room_joined':
        _updateStateManager({
          'currentRoomId': data['room_id'],
          'roomState': data['room_state'],
          'error': null
        });
        break;
      case 'error':
        _updateStateManager({
          'error': data['error'],
          'isLoading': false
        });
        break;
    }

    // Call registered handler if exists
    final handler = _eventHandlers[event];
    if (handler != null) {
      handler(eventData);
    }

    // Broadcast event to stream
    _eventStreamController.add(eventData);
  }

  /// Update StateManager with connection state
  void _updateStateManager(Map<String, dynamic> newState) {
    try {
      // We need to get the StateManager from the current context
      // For now, we'll store the state locally and update when context is available
      _pendingStateUpdate = newState;
    } catch (e) {
      _log.error("❌ Error updating StateManager: $e");
    }
  }

  /// Update StateManager with current context
  void _updateStateManagerWithContext(BuildContext context) {
    if (_pendingStateUpdate != null) {
      try {
        final stateManager = Provider.of<StateManager>(context, listen: false);
        
        // Ensure websocket state is registered
        if (!stateManager.isPluginStateRegistered("websocket")) {
          stateManager.registerPluginState("websocket", {
            'isConnected': false,
            'sessionId': null,
            'userId': null,
            'username': null,
            'currentRoomId': null,
            'roomState': null,
            'error': null,
            'connectionTime': null,
            'lastActivity': null,
          });
        }
        
        final currentState = stateManager.getPluginState<Map<String, dynamic>>("websocket") ?? {};
        stateManager.updatePluginState("websocket", {...currentState, ..._pendingStateUpdate!});
        _pendingStateUpdate = null;
      } catch (e) {
        _log.error("❌ Error updating StateManager with context: $e");
      }
    }
  }

  /// Register custom event handler
  void registerEventHandler(String event, Function(Map<String, dynamic>) handler) {
    _eventHandlers[event] = handler;
    _log.info("✅ Registered handler for event: $event");
  }

  /// Start token refresh timer
  void _startTokenRefreshTimer() {
    _stopTokenRefreshTimer();
    _tokenRefreshTimer = Timer.periodic(const Duration(minutes: 4), (timer) async {
      _log.info("🔄 Refreshing token...");
      final loginModule = _moduleManager.getModuleByType<LoginModule>();
      if (loginModule != null) {
        final hasToken = await loginModule.hasValidToken();
        if (!hasToken) {
          _log.error("❌ Token refresh failed, stopping timer");
          _stopTokenRefreshTimer();
        }
      }
    });
  }

  /// Stop token refresh timer
  void _stopTokenRefreshTimer() {
    _tokenRefreshTimer?.cancel();
    _tokenRefreshTimer = null;
  }

  /// Connect to WebSocket server
  Future<bool> connect(BuildContext context) async {
    if (!_isInitialized) {
      return await initialize(context);
    }

    if (_isConnected) {
      _log.info("✅ WebSocket already connected");
      return true;
    }

    // Ensure websocket state is registered
    final stateManager = Provider.of<StateManager>(context, listen: false);
    if (!stateManager.isPluginStateRegistered("websocket")) {
      stateManager.registerPluginState("websocket", {
        'isConnected': false,
        'sessionId': null,
        'userId': null,
        'username': null,
        'currentRoomId': null,
        'roomState': null,
        'error': null,
        'connectionTime': null,
        'lastActivity': null,
      });
    }

    // Check if we already have a connection from StateManager
    final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
    
    if (websocketState != null && websocketState['isConnected'] == true) {
      _log.info("✅ Using existing WebSocket connection from StateManager");
      _isConnected = true;
      _updateConnectionInfo(context);
      return true;
    }

    try {
      _log.info("🔄 Connecting to WebSocket server...");
      
      if (_socket == null) {
        _log.error("❌ Socket not initialized");
        return false;
      }
      
      _socket!.connect();
      
      // Wait for connection
      await Future.delayed(const Duration(seconds: 2));
      
      if (_isConnected) {
        _log.info("✅ WebSocket connected successfully");
        
        // Update StateManager with connection status
        final currentState = stateManager.getPluginState<Map<String, dynamic>>("websocket") ?? {};
        stateManager.updatePluginState("websocket", {
          ...currentState,
          'isConnected': true,
          'sessionId': _sessionId,
          'connectionTime': DateTime.now().toIso8601String(),
          'error': null
        });
        
        // Update any pending state updates
        _updateStateManagerWithContext(context);
        
        return true;
      } else {
        _log.error("❌ WebSocket connection failed");
        return false;
      }
    } catch (e) {
      _log.error("❌ Error connecting to WebSocket: $e");
      return false;
    }
  }

  /// Update connection info from StateManager
  void _updateConnectionInfo(BuildContext context) {
    try {
      final stateManager = Provider.of<StateManager>(context, listen: false);
      
      // Ensure websocket state is registered
      if (!stateManager.isPluginStateRegistered("websocket")) {
        stateManager.registerPluginState("websocket", {
          'isConnected': false,
          'sessionId': null,
          'userId': null,
          'username': null,
          'currentRoomId': null,
          'roomState': null,
          'error': null,
          'connectionTime': null,
          'lastActivity': null,
        });
      }
      
      final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
      
      if (websocketState != null) {
        _sessionId = websocketState['sessionId'];
        _userId = websocketState['userId'];
        _username = websocketState['username'];
        _isConnected = websocketState['isConnected'] ?? false;
        _currentRoomId = websocketState['currentRoomId'];
      }
    } catch (e) {
      _log.error("❌ Error updating connection info: $e");
    }
  }

  /// Disconnect from WebSocket server
  void disconnect() {
    try {
      _socket?.disconnect();
      _isConnected = false;
      _sessionId = null;
      _userId = null;
      _username = null;
      _currentRoomId = null;
      _stopTokenRefreshTimer();
      
      // Update StateManager with disconnect status
      _updateStateManager({
        'isConnected': false,
        'sessionId': null,
        'currentRoomId': null,
        'roomState': null,
        'error': null
      });
      
      _log.info("🔌 WebSocket disconnected");
    } catch (e) {
      _log.error("❌ Error disconnecting WebSocket: $e");
    }
  }

  /// Create a room
  Future<Map<String, dynamic>> createRoom(String userId, [Map<String, dynamic>? roomData]) async {
    if (!_isConnected || _socket == null) {
      _log.error("❌ Cannot create room: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    try {
      _log.info("🏠 Creating room for user: $userId");
      
      final data = {
        'user_id': userId,
        ...?roomData, // Spread room data if provided
      };

      // Create a completer to wait for the room_joined event (server response)
      final completer = Completer<Map<String, dynamic>>();
      
      // Set up a one-time listener for the room_joined event (server response to create_room)
      void onRoomJoined(dynamic eventData) {
        if (eventData is Map<String, dynamic>) {
          final roomId = eventData['room_id'];
          _currentRoomId = roomId;
          _rooms[roomId] = _rooms[roomId] ?? <String>{};
          _rooms[roomId]!.add(_socket!.id!);
          _sessionRooms[_socket!.id!] = _sessionRooms[_socket!.id!] ?? <String>{};
          _sessionRooms[_socket!.id!]!.add(roomId);
          completer.complete({
            "success": "Room created successfully", 
            "data": {
              'room_id': roomId,
              'current_size': eventData['current_size'],
              'max_size': eventData['max_size']
            }
          });
        }
      }

      // Set up a one-time listener for create room errors
      void onError(dynamic eventData) {
        if (eventData is Map<String, dynamic> && eventData['message']?.toString().contains('Failed to create room') == true) {
          completer.complete({"error": eventData['message']});
        }
      }

      // Add event listeners
      _socket!.on('room_joined', onRoomJoined);
      _socket!.on('create_room_error', onError);

      // Emit create_room event
      _socket!.emit('create_room', data);

      // Wait for the room_joined event with a timeout
      try {
        final result = await completer.future.timeout(
          const Duration(seconds: 5),
          onTimeout: () {
            return {"error": "Timeout waiting for room creation confirmation"};
          },
        );
        
        // Remove event listeners
        _socket!.off('room_joined', onRoomJoined);
        _socket!.off('create_room_error', onError);
        return result;
      } catch (e) {
        // Remove event listeners
        _socket!.off('room_joined', onRoomJoined);
        _socket!.off('create_room_error', onError);
        return {"error": "Failed to create room: $e"};
      }
      
    } catch (e) {
      _log.error("❌ Create room error: $e");
      return {"error": "Failed to create room: $e"};
    }
  }

  /// Join a room
  Future<Map<String, dynamic>> joinRoom(String roomId, {Map<String, dynamic>? data}) async {
    if (!_isConnected || _socket == null) {
      _log.error("❌ Cannot join room: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    try {
      _log.info("🚪 Joining room: $roomId");
      
      // Leave current room if any
      if (_currentRoomId != null) {
        await leaveRoom(_currentRoomId!);
      }

      // Create a completer to wait for the room_joined event
      final completer = Completer<Map<String, dynamic>>();
      
      // Set up a one-time listener for the room_joined event
      void onRoomJoined(dynamic eventData) {
        if (eventData is Map<String, dynamic> && eventData['room_id'] == roomId) {
          _currentRoomId = roomId;
          _rooms[roomId] = _rooms[roomId] ?? <String>{};
          _rooms[roomId]!.add(_socket!.id!);
          _sessionRooms[_socket!.id!] = _sessionRooms[_socket!.id!] ?? <String>{};
          _sessionRooms[_socket!.id!]!.add(roomId);
          completer.complete({"success": "Successfully joined room", "data": {'room_id': roomId}});
        }
      }

      // Set up a one-time listener for errors
      void onError(dynamic eventData) {
        if (eventData is Map<String, dynamic> && eventData['message']?.toString().contains('Failed to join room') == true) {
          completer.complete({"error": eventData['message']});
        }
      }

      // Add event listeners
      _socket!.on('room_joined', onRoomJoined);
      _socket!.on('join_room_error', onError);

      // Join new room
      _socket!.emit('join_room', {
        'room_id': roomId,
        if (data != null) ...data
      });

      // Wait for the room_joined event with a timeout
      try {
        final result = await completer.future.timeout(
          const Duration(seconds: 5),
          onTimeout: () {
            return {"error": "Timeout waiting for room join confirmation"};
          },
        );
        
        // Remove event listeners
        _socket!.off('room_joined', onRoomJoined);
        _socket!.off('join_room_error', onError);
        return result;
      } catch (e) {
        // Remove event listeners
        _socket!.off('room_joined', onRoomJoined);
        _socket!.off('join_room_error', onError);
        return {"error": "Failed to join room: $e"};
      }
    } catch (e) {
      _log.error("❌ Join room error: $e");
      return {"error": "Failed to join room: $e"};
    }
  }

  /// Leave a room
  Future<Map<String, dynamic>> leaveRoom(String roomId) async {
    if (!_isConnected || _socket == null) {
      _log.error("❌ Cannot leave room: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    try {
      _log.info("🚪 Leaving room: $roomId");
      
      _socket!.emit('leave_room', {
        'room_id': roomId
      });

      // Update state immediately for leave operations
      _rooms[roomId]?.remove(_socket!.id);
      _sessionRooms[_socket!.id]?.remove(roomId);
      
      if (_currentRoomId == roomId) {
        _currentRoomId = null;
      }

      _log.info("✅ Left room: $roomId");
      return {"success": "Successfully left room", "data": {'room_id': roomId}};
      
    } catch (e) {
      _log.error("❌ Leave room error: $e");
      return {"error": "Failed to leave room: $e"};
    }
  }

  /// Send a message to a room
  Future<Map<String, dynamic>> sendMessage(String message) async {
    if (!_isConnected || _socket == null) {
      _log.error("❌ Cannot send message: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    if (_currentRoomId == null) {
      _log.error("❌ Cannot send message: Not in a room");
      return {"error": "Not in a room"};
    }

    try {
      _log.info("📨 Sending message: $message");
      
      _socket!.emit('message', {
        'room_id': _currentRoomId,
        'message': message
      });
      
      _log.info("✅ Message sent successfully");
      return {"success": "Message sent successfully"};
      
    } catch (e) {
      _log.error("❌ Send message error: $e");
      return {"error": "Failed to send message: $e"};
    }
  }

  /// Press button (game functionality)
  Future<Map<String, dynamic>> pressButton() async {
    if (!_isConnected || _socket == null) {
      _log.error("❌ Cannot press button: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    if (_currentRoomId == null) {
      _log.error("❌ Cannot press button: Not in a room");
      return {"error": "Not in a room"};
    }

    try {
      _log.info("🔘 Pressing button");
      
      _socket!.emit('press_button', {
        'room_id': _currentRoomId
      });
      
      _log.info("✅ Button press sent");
      return {"success": "Button press sent"};
      
    } catch (e) {
      _log.error("❌ Press button error: $e");
      return {"error": "Failed to press button: $e"};
    }
  }

  /// Get counter (game functionality)
  Future<Map<String, dynamic>> getCounter() async {
    if (!_isConnected || _socket == null) {
      _log.error("❌ Cannot get counter: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    if (_currentRoomId == null) {
      _log.error("❌ Cannot get counter: Not in a room");
      return {"error": "Not in a room"};
    }

    try {
      _log.info("🔢 Getting counter");
      
      _socket!.emit('get_counter', {
        'room_id': _currentRoomId
      });
      
      _log.info("✅ Counter request sent");
      return {"success": "Counter request sent"};
      
    } catch (e) {
      _log.error("❌ Get counter error: $e");
      return {"error": "Failed to get counter: $e"};
    }
  }

  /// Get users in current room
  Future<Map<String, dynamic>> getUsers() async {
    if (!_isConnected || _socket == null) {
      _log.error("❌ Cannot get users: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    if (_currentRoomId == null) {
      _log.error("❌ Cannot get users: Not in a room");
      return {"error": "Not in a room"};
    }

    try {
      _log.info("👥 Getting users");
      
      _socket!.emit('get_users', {
        'room_id': _currentRoomId
      });
      
      _log.info("✅ Users request sent");
      return {"success": "Users request sent"};
      
    } catch (e) {
      _log.error("❌ Get users error: $e");
      return {"error": "Failed to get users: $e"};
    }
  }

  /// Emit event to specific room
  bool emitWithRoom(String event, String roomId, Map<String, dynamic> data) {
    if (_socket == null) {
      _log.error("❌ Cannot emit event: Socket not connected");
      return false;
    }

    try {
      _log.info("⚡ Emitting event to room: $event, room: $roomId");
      final eventData = {
        'room_id': roomId,
        ...data
      };
      _socket!.emit(event, eventData);
      return true;
    } catch (e) {
      _log.error("❌ Error emitting event to room: $e");
      return false;
    }
  }

  /// Emit event with acknowledgment
  bool emitWithAck(String event, Map<String, dynamic> data, Function(dynamic) ack) {
    if (_socket == null) {
      _log.error("❌ Cannot emit event with ACK: Socket not connected");
      return false;
    }

    try {
      _log.info("⚡ Emitting event with ACK: $event");
      _socket!.emitWithAck(event, data, ack: ack);
      return true;
    } catch (e) {
      _log.error("❌ Error emitting event with ACK: $e");
      return false;
    }
  }

  /// Clear all rooms
  void clearRooms() {
    _rooms.clear();
    _sessionRooms.clear();
    _currentRoomId = null;
  }

  /// Get connection status
  Map<String, dynamic> getConnectionStatus() {
    return {
      'isConnected': _isConnected,
      'isInitialized': _isInitialized,
      'sessionId': _sessionId,
      'userId': _userId,
      'username': _username,
      'currentRoomId': _currentRoomId,
      'rooms': _rooms,
      'sessionRooms': _sessionRooms,
    };
  }

  /// Reset the manager (for testing or reconnection)
  void reset() {
    _socket?.disconnect();
    _socket = null;
    _isInitialized = false;
    _isConnected = false;
    _sessionId = null;
    _userId = null;
    _username = null;
    _currentRoomId = null;
    _stopTokenRefreshTimer();
    clearRooms();
    _eventHandlers.clear();
    _log.info("🔄 WebSocket manager reset");
  }

  /// Dispose resources
  void dispose() {
    _stopTokenRefreshTimer();
    _eventStreamController.close();
    _eventHandlers.clear();
    clearRooms();
  }
} 