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
  
  // Event handling
  final StreamController<Map<String, dynamic>> _eventStreamController = StreamController<Map<String, dynamic>>.broadcast();
  final Map<String, Function(Map<String, dynamic>)> _eventHandlers = {};
  
  // Token management
  Timer? _tokenRefreshTimer;
  
  // State management
  Map<String, dynamic>? _pendingStateUpdate;
  
  // Module manager for accessing LoginModule
  final ModuleManager _moduleManager = ModuleManager();

  // Getters
  IO.Socket? get socket => _socket;
  bool get isInitialized => _isInitialized;
  Stream<Map<String, dynamic>> get eventStream => _eventStreamController.stream;

  /// Initialize the WebSocket manager
  Future<bool> initialize(BuildContext context) async {
    if (_isInitialized) {
      _log.info("✅ WebSocket manager already initialized");
      return isConnectedWithContext(context);
    }

    try {
      _log.info("🔄 Initializing WebSocket manager...");
      
      // Register websocket state in StateManager if not already registered
      final stateManager = Provider.of<StateManager>(context, listen: false);
      if (!stateManager.isPluginStateRegistered("websocket")) {
        stateManager.registerPluginState("websocket", {
          'connected': false,
          'sessionId': null,
          'userId': null,
          'username': null,
          'currentRoomId': null,
          'rooms': {},
          'sessionRooms': {},
          'error': null,
          'connectionTime': null,
          'lastActivity': null,
        });
        _log.info("✅ Registered websocket state in StateManager");
      }
      
      // Check if we already have a connection from StateManager
      final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
      
      if (websocketState != null && websocketState['connected'] == true) {
        _log.info("✅ Using existing WebSocket connection from StateManager");
        _isInitialized = true;
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
      _log.info("✅ Session ID: ${_socket!.id}");
      _handleEvent('connect', {});
    });

    _socket!.onDisconnect((_) {
      _log.info("❌ WebSocket disconnected");
      _handleEvent('disconnect', {});
    });

    _socket!.onConnectError((error) {
      _log.error("🚨 WebSocket connection error: $error");
      _handleEvent('error', {'error': error.toString()});
    });

    _socket!.on('session_data', (data) {
      _log.info("📋 Received session data from WebSocket server");
      _handleEvent('session_update', data);
    });

    _socket!.on('join_room_success', (data) {
      _log.info("🏠 Successfully joined room: $data");
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

    // Update StateManager based on event type (single source of truth)
    switch (event) {
      case 'connect':
        _updateStateManager({
          'connected': true,
          'sessionId': _socket?.id,
          'connectionTime': DateTime.now().toIso8601String(),
          'error': null
        });
        break;
      case 'disconnect':
        _updateStateManager({
          'connected': false,
          'sessionId': null,
          'currentRoomId': null,
          'error': null
        });
        break;
      case 'session_update':
        _updateStateManager({
          'userId': data['user_id'],
          'username': data['username'],
          'lastActivity': DateTime.now().toIso8601String(),
          'error': null
        });
        break;
      case 'room_joined':
        _updateStateManager({
          'currentRoomId': data['room_id'],
          'error': null
        });
        break;
      case 'error':
        _updateStateManager({
          'error': data['error'],
          'connected': false
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
            'connected': false,
            'sessionId': null,
            'userId': null,
            'username': null,
            'currentRoomId': null,
            'rooms': {},
            'sessionRooms': {},
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

    if (isConnectedWithContext(context)) {
      _log.info("✅ WebSocket already connected");
      return true;
    }

    // Ensure websocket state is registered
    final stateManager = Provider.of<StateManager>(context, listen: false);
    if (!stateManager.isPluginStateRegistered("websocket")) {
      stateManager.registerPluginState("websocket", {
        'connected': false,
        'sessionId': null,
        'userId': null,
        'username': null,
        'currentRoomId': null,
        'rooms': {},
        'sessionRooms': {},
        'error': null,
        'connectionTime': null,
        'lastActivity': null,
      });
    }

    // Check if we already have a connection from StateManager
    final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
    
    if (websocketState != null && websocketState['connected'] == true) {
      _log.info("✅ Using existing WebSocket connection from StateManager");
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
      
      // Check if socket is actually connected
      if (_socket!.connected) {
        _log.info("✅ WebSocket connected successfully");
        
        // Update StateManager with connection status
        final currentState = stateManager.getPluginState<Map<String, dynamic>>("websocket") ?? {};
        stateManager.updatePluginState("websocket", {
          ...currentState,
          'connected': true,
          'sessionId': _socket!.id,
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

  /// Check if connected using StateManager as primary source
  bool isConnectedWithContext(BuildContext context) {
    try {
      final stateManager = Provider.of<StateManager>(context, listen: false);
      final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
      return websocketState?['connected'] ?? false;
    } catch (e) {
      _log.error("❌ Error checking connection state: $e");
      return false;
    }
  }

  /// Get session ID from StateManager
  String? getSessionId(BuildContext context) {
    try {
      final stateManager = Provider.of<StateManager>(context, listen: false);
      final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
      return websocketState?['sessionId'];
    } catch (e) {
      _log.error("❌ Error getting session ID: $e");
      return null;
    }
  }

  /// Get current room ID from StateManager
  String? getCurrentRoomId(BuildContext context) {
    try {
      final stateManager = Provider.of<StateManager>(context, listen: false);
      final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
      return websocketState?['currentRoomId'];
    } catch (e) {
      _log.error("❌ Error getting current room ID: $e");
      return null;
    }
  }

  /// Disconnect from WebSocket server
  void disconnect() {
    try {
      _socket?.disconnect();
      _stopTokenRefreshTimer();
      
      // Update StateManager with disconnect status
      _updateStateManager({
        'connected': false,
        'sessionId': null,
        'currentRoomId': null,
        'error': null
      });
      
      _log.info("🔌 WebSocket disconnected");
    } catch (e) {
      _log.error("❌ Error disconnecting WebSocket: $e");
    }
  }

  /// Create a room
  Future<Map<String, dynamic>> createRoom(String userId, [Map<String, dynamic>? roomData]) async {
    if (_socket == null) {
      _log.error("❌ Cannot create room: Socket not initialized");
      return {"error": "Socket not initialized"};
    }
    
    // Check if socket is actually connected
    if (!_socket!.connected) {
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
        if (eventData is Map<String, dynamic>) {
          final message = eventData['message']?.toString() ?? '';
          if (message.contains('Failed to create room')) {
            completer.complete({"error": message});
          }
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
      _log.error("❌ Error creating room: $e");
      return {"error": "Failed to create room: $e"};
    }
  }

  /// Join a room
  Future<Map<String, dynamic>> joinRoom(String roomId, String userId) async {
    if (_socket == null) {
      _log.error("❌ Cannot join room: Socket not initialized");
      return {"error": "Socket not initialized"};
    }
    
    // Check if socket is actually connected
    if (!_socket!.connected) {
      _log.error("❌ Cannot join room: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    try {
      _log.info("🏠 Joining room: $roomId for user: $userId");
      
      final data = {
        'room_id': roomId,
        'user_id': userId,
      };

      // Create a completer to wait for the join_room_success event (server response)
      final completer = Completer<Map<String, dynamic>>();
      
      // Set up a one-time listener for the join_room_success event (server response)
      void onJoinSuccess(dynamic eventData) {
        if (eventData is Map<String, dynamic>) {
          completer.complete({
            "success": "Successfully joined room", 
            "data": {
              'room_id': roomId,
              'current_size': eventData['current_size'],
              'max_size': eventData['max_size']
            }
          });
        }
      }

      // Set up a one-time listener for join room errors
      void onError(dynamic eventData) {
        if (eventData is Map<String, dynamic>) {
          final message = eventData['message']?.toString() ?? '';
          if (message.contains('Failed to join room')) {
            completer.complete({"error": message});
          }
        }
      }

      // Add event listeners
      _socket!.on('join_room_success', onJoinSuccess);
      _socket!.on('join_room_error', onError);

      // Emit join_room event
      _socket!.emit('join_room', data);

      // Wait for the join_room_success event with a timeout
      try {
        final result = await completer.future.timeout(
          const Duration(seconds: 5),
          onTimeout: () {
            return {"error": "Timeout waiting for room join confirmation"};
          },
        );
        
        // Remove event listeners
        _socket!.off('join_room_success', onJoinSuccess);
        _socket!.off('join_room_error', onError);
        return result;
      } catch (e) {
        // Remove event listeners
        _socket!.off('join_room_success', onJoinSuccess);
        _socket!.off('join_room_error', onError);
        return {"error": "Failed to join room: $e"};
      }
      
    } catch (e) {
      _log.error("❌ Error joining room: $e");
      return {"error": "Failed to join room: $e"};
    }
  }

  /// Leave a room
  Future<Map<String, dynamic>> leaveRoom(String roomId) async {
    if (_socket == null) {
      _log.error("❌ Cannot leave room: Socket not initialized");
      return {"error": "Socket not initialized"};
    }
    
    // Check if socket is actually connected
    if (!_socket!.connected) {
      _log.error("❌ Cannot leave room: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    try {
      _log.info("🏠 Leaving room: $roomId");
      
      final data = {
        'room_id': roomId,
      };

      _socket!.emit('leave_room', data);
      
      return {"success": "Successfully left room"};
      
    } catch (e) {
      _log.error("❌ Error leaving room: $e");
      return {"error": "Failed to leave room: $e"};
    }
  }

  /// Send a message to a room
  Future<Map<String, dynamic>> sendMessage(String roomId, String message, [Map<String, dynamic>? additionalData]) async {
    if (_socket == null) {
      _log.error("❌ Cannot send message: Socket not initialized");
      return {"error": "Socket not initialized"};
    }
    
    // Check if socket is actually connected
    if (!_socket!.connected) {
      _log.error("❌ Cannot send message: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    try {
      _log.info("💬 Sending message to room: $roomId");
      
      final data = {
        'room_id': roomId,
        'message': message,
        ...?additionalData, // Spread additional data if provided
      };

      _socket!.emit('send_message', data);
      
      return {"success": "Message sent successfully"};
      
    } catch (e) {
      _log.error("❌ Error sending message: $e");
      return {"error": "Failed to send message: $e"};
    }
  }

  /// Broadcast a message to all connected clients
  Future<Map<String, dynamic>> broadcastMessage(String message, [Map<String, dynamic>? additionalData]) async {
    if (_socket == null) {
      _log.error("❌ Cannot broadcast message: Socket not initialized");
      return {"error": "Socket not initialized"};
    }
    
    // Check if socket is actually connected
    if (!_socket!.connected) {
      _log.error("❌ Cannot broadcast message: WebSocket not connected");
      return {"error": "WebSocket not connected"};
    }

    try {
      _log.info("📢 Broadcasting message to all clients");
      
      final data = {
        'message': message,
        ...?additionalData, // Spread additional data if provided
      };

      _socket!.emit('broadcast', data);
      
      return {"success": "Message broadcasted successfully"};
      
    } catch (e) {
      _log.error("❌ Error broadcasting message: $e");
      return {"error": "Failed to broadcast message: $e"};
    }
  }

  /// Get current connection status
  Map<String, dynamic> getStatus(BuildContext context) {
    try {
      final stateManager = Provider.of<StateManager>(context, listen: false);
      final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
      
      return {
        'isInitialized': _isInitialized,
        'connected': websocketState?['connected'] ?? false,
        'sessionId': websocketState?['sessionId'],
        'userId': websocketState?['userId'],
        'username': websocketState?['username'],
        'currentRoomId': websocketState?['currentRoomId'],
        'rooms': websocketState?['rooms'] ?? {},
        'sessionRooms': websocketState?['sessionRooms'] ?? {},
        'error': websocketState?['error'],
        'connectionTime': websocketState?['connectionTime'],
        'lastActivity': websocketState?['lastActivity'],
      };
    } catch (e) {
      _log.error("❌ Error getting status: $e");
      return {
        'isInitialized': _isInitialized,
        'connected': false,
        'sessionId': null,
        'userId': null,
        'username': null,
        'currentRoomId': null,
        'rooms': {},
        'sessionRooms': {},
        'error': 'Failed to get status from StateManager',
      };
    }
  }

  /// Dispose of the WebSocket manager
  void dispose() {
    try {
      _socket?.disconnect();
      _socket = null;
      _stopTokenRefreshTimer();
      _eventStreamController.close();
      _eventHandlers.clear();
      _isInitialized = false;
      
      _log.info("🗑️ WebSocket manager disposed");
    } catch (e) {
      _log.error("❌ Error disposing WebSocket manager: $e");
    }
  }
} 