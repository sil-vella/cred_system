import 'package:socket_io_client/socket_io_client.dart' as IO;
import '../../../../../../tools/logging/logger.dart';
import '../../../../../../utils/consts/config.dart';

class SocketConnectionManager {
  static final Logger _log = Logger();
  IO.Socket? _socket;
  bool _isConnected = false;
  final Function(IO.Socket) _setupEventHandlers;

  SocketConnectionManager(this._setupEventHandlers);

  bool get isConnected => _isConnected;
  IO.Socket? get socket => _socket;

  Future<bool> connect(String accessToken) async {
    try {
      _log.info("⚡ Connecting to WebSocket server...");
      _log.info("🔧 Connection options: {");
      _log.info("   - transports: ['websocket']");
      _log.info("   - autoConnect: false");
      _log.info("   - reconnection: true");
      _log.info("   - reconnectionAttempts: 3");
      _log.info("   - reconnectionDelay: 1000");
      _log.info("   - reconnectionDelayMax: 5000");
      _log.info("   - timeout: 20000");
      _log.info("   - forceNew: true");
      _log.info("}");
      
      // Disconnect existing socket if any
      await disconnect();

      // Create new socket connection
      _socket = IO.io(Config.wsUrl, <String, dynamic>{
        'transports': ['websocket'],
        'autoConnect': false,
        'query': {
          'token': accessToken
        },
        'reconnection': true,
        'reconnectionAttempts': 3,
        'reconnectionDelay': 1000,
        'reconnectionDelayMax': 5000,
        'timeout': 20000,
        'forceNew': true
      });

      // Set up event handlers
      _setupEventHandlers(_socket!);

      // Connect to server
      _log.info("🔌 Connecting socket...");
      _socket!.connect();

      // Wait for connection to be established
      await Future.delayed(const Duration(milliseconds: 500));
      
      if (_socket!.connected) {
        _isConnected = true;
        _log.info("✅ Connected to WebSocket server with session ID: ${_socket!.id}");
        return true;
      } else {
        _log.error("❌ Failed to establish WebSocket connection");
        await disconnect();
        return false;
      }

    } catch (e) {
      _log.error("❌ WebSocket connection error: $e");
      await disconnect();
      return false;
    }
  }

  Future<void> disconnect() async {
    try {
      // Disconnect socket
      if (_socket != null) {
        _socket!.disconnect();
        _socket = null;
      }
      
      // Clear state
      _isConnected = false;
      
      _log.info("✅ WebSocket disconnected");
    } catch (e) {
      _log.error("❌ Error during disconnect: $e");
    }
  }
} 