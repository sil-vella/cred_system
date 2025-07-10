import 'package:socket_io_client/socket_io_client.dart' as IO;
import '../../../../../../tools/logging/logger.dart';
import 'result_handler.dart';
import 'dart:async';

class RoomManager {
  static final Logger _log = Logger();
  final Map<String, Set<String>> _rooms = {};
  final Map<String, Set<String>> _sessionRooms = {};
  String? _currentRoomId;
  IO.Socket? _socket;
  final ResultHandler _resultHandler = ResultHandler();

  RoomManager(this._socket);

  String? get currentRoomId => _currentRoomId;
  set currentRoomId(String? value) => _currentRoomId = value;
  Map<String, Set<String>> get rooms => _rooms;
  Map<String, Set<String>> get sessionRooms => _sessionRooms;

  void setSocket(IO.Socket socket) {
    _socket = socket;
  }

  Future<WebSocketResult> joinRoom(String roomId, {Map<String, dynamic>? data}) async {
    if (_socket == null) {
      return _resultHandler.createNoConnectionResult();
    }

    try {
      _log.info("🚪 Joining room: $roomId");
      
      // Leave current room if any
      if (_currentRoomId != null) {
        await leaveRoom(_currentRoomId!);
      }

      // Create a completer to wait for the room_joined event
      final completer = Completer<WebSocketResult>();
      
      // Set up a one-time listener for the room_joined event
      void onRoomJoined(data) {
        if (data['room_id'] == roomId) {
          _currentRoomId = roomId;
          _rooms[roomId] = _rooms[roomId] ?? {};
          _rooms[roomId]!.add(_socket!.id!);
          _sessionRooms[_socket!.id!] = _sessionRooms[_socket!.id!] ?? {};
          _sessionRooms[_socket!.id!]!.add(roomId);
          completer.complete(_resultHandler.createSuccessResult('join_room', data: {'room_id': roomId}));
        }
      }

      // Set up a one-time listener for errors
      void onError(data) {
        if (data['message']?.contains('Failed to join room') == true) {
          completer.complete(_resultHandler.createErrorResult('join_room', data['message']));
        }
      }

      // Add event listeners
      _socket!.on('room_joined', onRoomJoined);
      _socket!.on('error', onError);

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
            return _resultHandler.createErrorResult('join_room', 'Timeout waiting for room join confirmation');
          },
        );
        
        // Remove event listeners
        _socket!.off('room_joined', onRoomJoined);
        _socket!.off('error', onError);
        return result;
      } catch (e) {
        // Remove event listeners
        _socket!.off('room_joined', onRoomJoined);
        _socket!.off('error', onError);
        return _resultHandler.createUnknownErrorResult('join_room', e.toString());
      }
    } catch (e) {
      _log.error("❌ Error joining room: $e");
      return _resultHandler.createUnknownErrorResult('join_room', e.toString());
    }
  }

  Future<WebSocketResult> leaveRoom(String roomId) async {
    if (_socket == null) {
      return _resultHandler.createNoConnectionResult();
    }

    try {
      _log.info("🚪 Leaving room: $roomId");
      
      // Leave room
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
      return _resultHandler.createSuccessResult('leave_room', data: {'room_id': roomId});
    } catch (e) {
      _log.error("❌ Error leaving room: $e");
      return _resultHandler.createUnknownErrorResult('leave_room', e.toString());
    }
  }

  void clearRooms() {
    _rooms.clear();
    _sessionRooms.clear();
    _currentRoomId = null;
  }
} 