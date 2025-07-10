import 'package:socket_io_client/socket_io_client.dart' as IO;
import '../../../../../../tools/logging/logger.dart';

class BroadcastManager {
  static final Logger _log = Logger();
  IO.Socket? _socket;

  void setSocket(IO.Socket socket) {
    _socket = socket;
  }

  bool emit(String event, Map<String, dynamic> data) {
    if (_socket == null) {
      _log.error("❌ Cannot emit event: Socket not connected");
      return false;
    }

    try {
      _log.info("⚡ Emitting event: $event");
      _socket!.emit(event, data);
      return true;
    } catch (e) {
      _log.error("❌ Error emitting event: $e");
      return false;
    }
  }

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
} 