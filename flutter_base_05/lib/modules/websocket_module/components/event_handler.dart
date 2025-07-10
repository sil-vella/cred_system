import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'dart:async';
import '../../../../../../tools/logging/logger.dart';
import '../../../../../../core/managers/state_manager.dart';
import 'websocket_state.dart';

class EventHandler {
  static final Logger _log = Logger();
  final StreamController<Map<String, dynamic>> _eventStreamController = StreamController<Map<String, dynamic>>.broadcast();
  final Map<String, Function(Map<String, dynamic>)> _eventHandlers = {};
  IO.Socket? _socket;
  late StateManager _stateManager;

  Stream<Map<String, dynamic>> get eventStream => _eventStreamController.stream;

  void setSocket(IO.Socket socket) {
    _socket = socket;
  }

  void setStateManager(StateManager stateManager) {
    _stateManager = stateManager;
  }

  void registerHandler(String event, Function(Map<String, dynamic>) handler) {
    _eventHandlers[event] = handler;
    _log.info("✅ Registered handler for event: $event");
  }

  void setupEventHandlers() {
    if (_socket == null) {
      _log.error("❌ Cannot setup event handlers: Socket not connected");
      return;
    }

    // Connection events
    _socket!.onConnect((_) {
      _log.info("✅ Connected to WebSocket server");
      _handleEvent('connect', {});
    });

    _socket!.onDisconnect((_) {
      _log.info("❌ Disconnected from WebSocket server");
      _handleEvent('disconnect', {});
    });

    _socket!.onError((error) {
      _log.error("❌ WebSocket error: $error");
      _handleEvent('error', {'error': error.toString()});
    });

    // Session events
    _socket!.on('session_update', (data) {
      _log.info("✅ Session updated: $data");
      _handleEvent('session_update', data);
    });

    _socket!.on('session_error', (data) {
      _log.error("❌ Session error: $data");
      _handleEvent('session_error', data);
    });

    // Register custom event handlers
    _eventHandlers.forEach((event, handler) {
      _socket!.on(event, (data) {
        _log.info("📨 Received custom event '$event': $data");
        _handleEvent(event, data);
      });
    });
  }

  void _handleEvent(String event, Map<String, dynamic> data) {
    // Add event type to data
    final eventData = {
      'event': event,
      ...data
    };

    // Update state based on event
    switch (event) {
      case 'connect':
        _updateState({
          'isConnected': true,
          'sessionId': _socket?.id,
          'connectionTime': DateTime.now().toIso8601String(),
          'error': null
        });
        break;
      case 'disconnect':
        _updateState({
          'isConnected': false,
          'sessionId': null,
          'currentRoomId': null,
          'roomState': null,
          'error': null
        });
        break;
      case 'session_update':
        _updateState({
          'sessionData': data['session_data'],
          'userId': data['user_id'],
          'username': data['username'],
          'lastActivity': DateTime.now().toIso8601String(),
          'error': null
        });
        break;
      case 'room_joined':
        _updateState({
          'currentRoomId': data['room_id'],
          'roomState': data['room_state'],
          'joinedRooms': [...(_stateManager.getPluginState<Map<String, dynamic>>("websocket")?['joinedRooms'] ?? []), data['room_id']],
          'error': null
        });
        break;
      case 'room_state':
        _updateState({
          'roomState': data['room_state'],
          'error': null
        });
        break;
      case 'error':
        _updateState({
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

  void _updateState(Map<String, dynamic> newState) {
    final currentState = _stateManager.getPluginState<Map<String, dynamic>>("websocket") ?? {};
    _stateManager.updatePluginState("websocket", {...currentState, ...newState});
  }

  void dispose() {
    _eventStreamController.close();
    _eventHandlers.clear();
  }
} 