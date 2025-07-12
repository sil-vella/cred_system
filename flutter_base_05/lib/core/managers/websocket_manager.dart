import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'dart:async';
import 'dart:convert';
import '../../tools/logging/logger.dart';
import '../../utils/consts/config.dart';
import '../../modules/login_module/login_module.dart';
import '../managers/module_manager.dart';
import '../models/websocket_events.dart';

class WebSocketManager {
  static final WebSocketManager _instance = WebSocketManager._internal();
  factory WebSocketManager() {
    Logger().info("🔍 WebSocketManager factory called - returning singleton instance");
    return _instance;
  }
  WebSocketManager._internal() {
    Logger().info("🔍 WebSocketManager singleton instance created");
  }

  static final Logger _log = Logger();
  
  IO.Socket? _socket;
  bool _isInitialized = false;
  bool _isConnected = false; // Track connection state explicitly
  bool _isConnecting = false; // Track if we're in the process of connecting
  
  // Event streams for UI updates
  final StreamController<WebSocketEvent> _eventController = StreamController<WebSocketEvent>.broadcast();
  final StreamController<ConnectionStatusEvent> _connectionController = StreamController<ConnectionStatusEvent>.broadcast();
  final StreamController<MessageEvent> _messageController = StreamController<MessageEvent>.broadcast();
  final StreamController<RoomEvent> _roomController = StreamController<RoomEvent>.broadcast();
  final StreamController<ErrorEvent> _errorController = StreamController<ErrorEvent>.broadcast();
  
  // Event handling
  final Map<String, Function(Map<String, dynamic>)> _eventHandlers = {};
  
  // Token management
  Timer? _tokenRefreshTimer;
  
  // Module manager for accessing LoginModule
  final ModuleManager _moduleManager = ModuleManager();

  // Getters
  IO.Socket? get socket => _socket;
  bool get isInitialized => _isInitialized;
  
  // Event streams for UI
  Stream<WebSocketEvent> get events => _eventController.stream;
  Stream<ConnectionStatusEvent> get connectionStatus => _connectionController.stream;
  Stream<MessageEvent> get messages => _messageController.stream;
  Stream<RoomEvent> get roomEvents => _roomController.stream;
  Stream<ErrorEvent> get errors => _errorController.stream;
  
  // Static getter for easy access
  static WebSocketManager get instance {
    Logger().info("🔍 WebSocketManager.instance getter called");
    return _instance;
  }

  /// Check if connected - direct socket check (no context needed)
  bool get isConnected {
    // Use both our tracked state and socket state for reliability
    final socketConnected = _socket?.connected ?? false;
    
    // If socket is connected but our tracked state is false, update it
    if (socketConnected && !_isConnected) {
      _log.info("🔍 Fixing tracked state: socket is connected but tracked state is false");
      _isConnected = true;
      _isConnecting = false; // We're no longer connecting
    }
    
    // If we have a socket but it's not connected, but we think we're connected, reset
    if (_socket != null && !socketConnected && _isConnected) {
      _log.info("🔍 Fixing tracked state: socket is not connected but tracked state is true");
      _isConnected = false;
    }
    
    final connected = _isConnected && socketConnected;
    _log.info("🔍 Connection check: tracked=$_isConnected, socket=$socketConnected, connecting=$_isConnecting, final=$connected, socket_id=${_socket?.id}");
    
    return connected;
  }

  /// Check if we're in the process of connecting
  bool get isConnecting => _isConnecting;

  /// Force refresh connection state (for debugging)
  void _refreshConnectionState() {
    final socketConnected = _socket?.connected ?? false;
    if (socketConnected != _isConnected) {
      _log.info("🔍 Refreshing connection state: socket=$socketConnected, tracked=$_isConnected");
      _isConnected = socketConnected;
    }
  }

  /// Initialize the WebSocket manager
  Future<bool> initialize() async {
    if (_isInitialized) {
      _log.info("✅ WebSocket manager already initialized");
      return isConnected;
    }

    try {
      _log.info("🔄 Initializing WebSocket manager...");
      
      // Check if socket is already connected
      _log.info("🔍 Checking socket connection in initialize: socket=${_socket != null}, connected=${_socket?.connected ?? false}, tracked=$_isConnected");
      
      // Refresh connection state before checking
      _refreshConnectionState();
      
      if (_socket != null && _socket!.connected && _isConnected) {
        _log.info("✅ WebSocket socket is already connected");
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
      _log.info("🔍 Creating new Socket.IO connection...");
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
      _log.info("🔍 Socket created: ${_socket != null}");

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
    
    // Use 'connect' event instead of onConnect to avoid conflicts with one-time listeners
    _socket!.on('connect', (_) {
      _log.info("✅ WebSocket connected successfully");
      _log.info("✅ Session ID: ${_socket!.id}");
      _log.info("🔍 Socket state after connect: connected=${_socket!.connected}");
      
      // Update our tracked connection state
      _isConnected = true;
      _isConnecting = false; // Reset connecting state
      _log.info("🔍 Updated tracked connection state: $_isConnected");
      
      // Emit connection event
      final event = ConnectionStatusEvent(
        status: ConnectionStatus.connected,
        sessionId: _socket!.id,
      );
      _connectionController.add(event);
      _eventController.add(event);
      
      _handleEvent('connect', {});
    });

    _socket!.onDisconnect((_) {
      _log.info("❌ WebSocket disconnected");
      _log.info("🔍 Socket state after disconnect: connected=${_socket!.connected}");
      
      // Update our tracked connection state
      _isConnected = false;
      
      // Emit disconnection event
      final event = ConnectionStatusEvent(
        status: ConnectionStatus.disconnected,
      );
      _connectionController.add(event);
      _eventController.add(event);
      
      _handleEvent('disconnect', {});
    });

    // Use 'connect_error' event instead of onConnectError to avoid conflicts
    _socket!.on('connect_error', (error) {
      _log.error("🚨 WebSocket connection error: $error");
      
      // Update our tracked connection state
      _isConnected = false;
      _isConnecting = false; // Reset connecting state
      
      // Emit error event
      final event = ConnectionStatusEvent(
        status: ConnectionStatus.error,
        error: error.toString(),
      );
      _connectionController.add(event);
      _eventController.add(event);
      
      _handleEvent('error', {'error': error.toString()});
    });

    _socket!.on('session_data', (data) {
      _log.info("📋 Received session data from WebSocket server");
      
      // Emit session data event
      final event = SessionDataEvent(data);
      _eventController.add(event);
      
      _handleEvent('session_update', data);
    });

    _socket!.on('join_room_success', (data) {
      _log.info("🏠 Successfully joined room: $data");
      
      // Emit room event
      final event = RoomEvent(
        roomId: data['room_id'] ?? '',
        roomData: data,
        action: 'joined',
      );
      _roomController.add(event);
      _eventController.add(event);
      
      _handleEvent('room_joined', data);
    });

    _socket!.on('join_room_error', (data) {
      _log.error("🚨 Failed to join room: $data");
      
      // Emit error event
      final errorEvent = ErrorEvent(
        'Failed to join room',
        details: data.toString(),
      );
      _errorController.add(errorEvent);
      _eventController.add(errorEvent);
      
      _handleEvent('join_room_error', data);
    });

    _socket!.on('create_room_success', (data) {
      _log.info("🏠 Successfully created room");
      
      // Emit room event
      final event = RoomEvent(
        roomId: data['room_id'] ?? '',
        roomData: data,
        action: 'created',
      );
      _roomController.add(event);
      _eventController.add(event);
      
      _handleEvent('create_room_success', data);
    });

    _socket!.on('create_room_error', (data) {
      _log.error("🚨 Failed to create room: $data");
      
      // Emit error event
      final errorEvent = ErrorEvent(
        'Failed to create room',
        details: data.toString(),
      );
      _errorController.add(errorEvent);
      _eventController.add(errorEvent);
      
      _handleEvent('create_room_error', data);
    });

    _socket!.on('message', (data) {
      _log.info("💬 Received message: $data");
      
      // Emit message event
      final event = MessageEvent(
        roomId: data['room_id'] ?? '',
        message: data['message'] ?? '',
        sender: data['sender'] ?? 'unknown',
        additionalData: data,
      );
      _messageController.add(event);
      _eventController.add(event);
      
      _handleEvent('message', data);
    });

    _socket!.on('error', (data) {
      _log.error("🚨 WebSocket error: $data");
      
      // Emit error event
      final errorEvent = ErrorEvent(
        'WebSocket error',
        details: data.toString(),
      );
      _errorController.add(errorEvent);
      _eventController.add(errorEvent);
      
      _handleEvent('error', data);
    });

    // Register custom event handlers
    _eventHandlers.forEach((event, handler) {
      _socket!.on(event, (data) {
        _log.info("📨 Received custom event '$event': $data");
        
        // Emit custom event
        final customEvent = CustomEvent(event, data);
        _eventController.add(customEvent);
        
        _handleEvent(event, data);
      });
    });
  }

  /// Handle events and broadcast to stream
  void _handleEvent(String event, Map<String, dynamic> data) {
    // Call registered handler if exists
    final handler = _eventHandlers[event];
    if (handler != null) {
      handler(data);
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
  Future<bool> connect() async {
    if (!_isInitialized) {
      final initialized = await initialize();
      if (!initialized) {
        return false;
      }
      // Continue with connection after initialization
    }

    // Check if the socket is already connected
    _log.info("🔍 Checking if socket is already connected...");
    
    // Refresh connection state before checking
    _refreshConnectionState();
    
    if (isConnected) {
      _log.info("✅ WebSocket socket is already connected");
      return true;
    }
    
    // Check if we're already connecting
    if (_isConnecting) {
      _log.info("🔄 WebSocket is already connecting, waiting...");
      return false;
    }
    
    _log.info("🔍 Socket not connected, proceeding with new connection...");
    _log.info("🔍 Connection state: tracked=$_isConnected, socket=${_socket?.connected ?? false}");

    try {
      _log.info("🔄 Connecting to WebSocket server...");
      
      // Set connecting state
      _isConnecting = true;
      
      if (_socket == null) {
        _log.error("❌ Socket not initialized");
        _isConnecting = false;
        return false;
      }
      
      // Emit connecting event
      final connectingEvent = ConnectionStatusEvent(
        status: ConnectionStatus.connecting,
      );
      _connectionController.add(connectingEvent);
      _eventController.add(connectingEvent);
      
      // Create a completer to wait for the connection event
      final completer = Completer<bool>();
      
      // Set up a one-time listener for the connect event
      void onConnect(dynamic _) {
        _log.info("✅ WebSocket connected successfully");
        _log.info("✅ Session ID: ${_socket!.id}");
        
        // Update our tracked connection state
        _isConnected = true;
        _isConnecting = false; // Reset connecting state
        
        completer.complete(true);
      }
      
      // Set up a one-time listener for connection errors
      void onConnectError(dynamic error) {
        _log.error("❌ WebSocket connection error: $error");
        
        // Update our tracked connection state
        _isConnected = false;
        _isConnecting = false;
        
        completer.complete(false);
      }
      
      // Add one-time event listeners (these will be removed after use)
      _socket!.once('connect', onConnect);
      _socket!.once('connect_error', onConnectError);
      
      // Start connection
      _socket!.connect();
      
      // Wait for connection with timeout
      try {
        final result = await completer.future.timeout(
          const Duration(seconds: 5),
          onTimeout: () {
            _log.error("❌ WebSocket connection timeout");
            _isConnecting = false; // Reset connecting state on timeout
            return false;
          },
        );
        
        return result;
      } catch (e) {
        _log.error("❌ WebSocket connection exception: $e");
        _isConnecting = false; // Reset connecting state on exception
        return false;
      }
      
    } catch (e) {
      _log.error("❌ Error connecting to WebSocket: $e");
      _isConnecting = false; // Reset connecting state on error
      return false;
    }
  }

  /// Disconnect from WebSocket server
  void disconnect() {
    try {
      _socket?.disconnect();
      _stopTokenRefreshTimer();
      
      // Update our tracked connection state
      _isConnected = false;
      
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
  Map<String, dynamic> getStatus() {
    return {
      'isInitialized': _isInitialized,
      'connected': isConnected,
      'sessionId': _socket?.id,
      'error': null,
      'connectionTime': null,
      'lastActivity': null,
    };
  }

  /// Dispose of the WebSocket manager
  void dispose() {
    try {
      _socket?.disconnect();
      _socket = null;
      _stopTokenRefreshTimer();
      _eventController.close();
      _connectionController.close();
      _messageController.close();
      _roomController.close();
      _errorController.close();
      _eventHandlers.clear();
      _isInitialized = false;
      
      _log.info("🗑️ WebSocket manager disposed");
    } catch (e) {
      _log.error("❌ Error disposing WebSocket manager: $e");
    }
  }
} 