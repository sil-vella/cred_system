import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import '../../core/00_base/module_base.dart';
import '../../core/managers/module_manager.dart';
import '../../core/managers/services_manager.dart';
import '../../core/managers/state_manager.dart';
import '../../core/services/shared_preferences.dart';
import '../../tools/logging/logger.dart';
import '../connections_api_module/connections_api_module.dart';
import 'components/event_handler.dart';
import 'components/socket_connection_manager.dart';
import 'components/room_manager.dart';
import 'components/session_manager.dart';
import 'components/token_manager.dart';
import 'components/result_handler.dart';
import 'components/broadcast_manager.dart';
import 'components/message_manager.dart';

class WebSocketModule extends ModuleBase {
  static final Logger _log = Logger();
  late ServicesManager _servicesManager;
  late ModuleManager _localModuleManager;
  StateManager? _stateManager;
  SharedPrefManager? _sharedPref;
  ConnectionsApiModule? _connectionModule;
  BuildContext? _currentContext;
  bool _mounted = true;

  // Components
  SocketConnectionManager? _socketManager;
  RoomManager? _roomManager;
  SessionManager? _sessionManager;
  TokenManager? _tokenManager;
  EventHandler? _eventHandler;
  ResultHandler? _resultHandler;
  BroadcastManager? _broadcastManager;
  MessageManager? _messageManager;

  // Getter for socket
  IO.Socket? get socket => _socketManager?.socket;

  /// ✅ Constructor with module key and dependencies
  WebSocketModule() : super("websocket_module", dependencies: ["connections_api_module"]);

  @override
  void initialize(BuildContext context, ModuleManager moduleManager) {
    super.initialize(context, moduleManager);
    _localModuleManager = moduleManager;
    _initDependencies(context);
    _log.info('✅ WebSocketModule initialized with context.');
  }

  void _initDependencies(BuildContext context) {
    try {
      _servicesManager = Provider.of<ServicesManager>(context, listen: false);
      _stateManager = Provider.of<StateManager>(context, listen: false);
      _sharedPref = _servicesManager.getService<SharedPrefManager>('shared_pref');
      _connectionModule = _localModuleManager.getModuleByType<ConnectionsApiModule>();
      _currentContext = context;

      if (_stateManager == null) {
        _log.error("❌ StateManager not available");
        return;
      }

      // Initialize components
      _socketManager = SocketConnectionManager(_setupEventHandlers);
      _roomManager = RoomManager(_socketManager?.socket);
      _sessionManager = SessionManager();
      _tokenManager = TokenManager(_connectionModule);
      _eventHandler = EventHandler();
      _resultHandler = ResultHandler();
      _broadcastManager = BroadcastManager();
      _messageManager = MessageManager(_roomManager!, _socketManager!);

      // Pass StateManager to EventHandler
      _eventHandler?.setStateManager(_stateManager!);

      // Initialize state in StateManager
      _stateManager!.registerPluginState("websocket", <String, dynamic>{
        "isConnected": false,
        "sessionId": null,
        "userId": null,
        "username": null,
        "currentRoomId": null,
        "roomState": null,
        "joinedRooms": [],
        "sessionData": null,
        "lastActivity": null,
        "connectionTime": null,
        "error": null,
        "isLoading": false,
        "hasValidToken": false
      });

      // Update TokenManager with the connection module
      _tokenManager?.setStateManager(_stateManager!);
    } catch (e) {
      _log.error("❌ Error initializing dependencies: $e");
    }
  }

  void _setupEventHandlers(IO.Socket socket) {
    _roomManager?.setSocket(socket);
    _eventHandler?.setSocket(socket);
    _broadcastManager?.setSocket(socket);
    _eventHandler?.setupEventHandlers();
  }

  /// ✅ Connect to WebSocket server
  Future<Map<String, dynamic>> connect(BuildContext context, {String? roomId}) async {
    _initDependencies(context);
    
    if (_connectionModule == null) {
      _log.error("❌ Connection module not available.");
      return {"error": "Service not available."};
    }

    try {
      _log.info("🔌 Connecting to WebSocket server...");
      
      // Get authentication token
      final token = await _connectionModule!.getAccessToken();
      if (token == null) {
        _log.error("❌ No authentication token available.");
        return {"error": "Authentication required."};
      }

      // Connect to WebSocket
      final success = await _socketManager?.connect(token) ?? false;
      
      if (success) {
        _log.info("✅ WebSocket connected successfully");
        return {"success": "Connected to WebSocket server"};
      } else {
        _log.error("❌ WebSocket connection failed");
        return {"error": "Connection failed"};
      }
    } catch (e) {
      _log.error("❌ WebSocket connection error: $e");
      return {"error": "Connection failed: $e"};
    }
  }

  /// ✅ Disconnect from WebSocket server
  Future<Map<String, dynamic>> disconnect() async {
    try {
      _log.info("🔌 Disconnecting from WebSocket server...");
      await _socketManager?.disconnect();
      _log.info("✅ WebSocket disconnected successfully");
      return {"success": "Disconnected from WebSocket server"};
    } catch (e) {
      _log.error("❌ WebSocket disconnection error: $e");
      return {"error": "Disconnection failed: $e"};
    }
  }

  /// ✅ Join a room
  Future<Map<String, dynamic>> joinRoom(String roomId) async {
    try {
      _log.info("🚪 Joining room: $roomId");
      final result = await _roomManager?.joinRoom(roomId);
      
      if (result?.isSuccess == true) {
        _log.info("✅ Joined room: $roomId");
        return {"success": "Joined room: $roomId"};
      } else {
        _log.error("❌ Failed to join room: ${result?.error}");
        return {"error": result?.error ?? "Failed to join room"};
      }
    } catch (e) {
      _log.error("❌ Join room error: $e");
      return {"error": "Failed to join room: $e"};
    }
  }

  /// ✅ Leave a room
  Future<Map<String, dynamic>> leaveRoom(String roomId) async {
    try {
      _log.info("🚪 Leaving room: $roomId");
      final result = await _roomManager?.leaveRoom(roomId);
      
      if (result?.isSuccess == true) {
        _log.info("✅ Left room: $roomId");
        return {"success": "Left room: $roomId"};
      } else {
        _log.error("❌ Failed to leave room: ${result?.error}");
        return {"error": result?.error ?? "Failed to leave room"};
      }
    } catch (e) {
      _log.error("❌ Leave room error: $e");
      return {"error": "Failed to leave room: $e"};
    }
  }

  /// ✅ Send a message
  Future<Map<String, dynamic>> sendMessage(String message, {String? roomId}) async {
    try {
      _log.info("📤 Sending message: $message");
      final result = await _messageManager?.sendMessage(message);
      
      if (result?.isSuccess == true) {
        _log.info("✅ Message sent successfully");
        return {"success": "Message sent"};
      } else {
        _log.error("❌ Failed to send message: ${result?.error}");
        return {"error": result?.error ?? "Failed to send message"};
      }
    } catch (e) {
      _log.error("❌ Send message error: $e");
      return {"error": "Failed to send message: $e"};
    }
  }

  @override
  void dispose() {
    _mounted = false;
    // Check if _socketManager has been initialized before calling disconnect
    try {
      if (_socketManager != null) {
        _socketManager?.disconnect();
      }
    } catch (e) {
      _log.error("❌ Error disposing WebSocket module: $e");
    }
    super.dispose();
  }
} 