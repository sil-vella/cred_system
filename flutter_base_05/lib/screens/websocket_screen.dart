import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'dart:convert';
import '../core/00_base/screen_base.dart';
import '../utils/consts/config.dart';
import '../modules/login_module/login_module.dart';
import '../core/managers/module_manager.dart';

class WebSocketScreen extends BaseScreen {
  const WebSocketScreen({Key? key}) : super(key: key);

  @override
  String computeTitle(BuildContext context) => 'WebSocket Test';

  @override
  BaseScreenState<WebSocketScreen> createState() => _WebSocketScreenState();
}

class _WebSocketScreenState extends BaseScreenState<WebSocketScreen> {
  IO.Socket? socket;
  bool isConnected = false;
  List<String> messages = [];
  String connectionStatus = 'Disconnected';
  Map<String, dynamic>? sessionData;
  String? sessionId;
  
  // Controllers for input fields
  final TextEditingController _roomIdController = TextEditingController();
  final TextEditingController _messageController = TextEditingController();
  final TextEditingController _customMessageController = TextEditingController();
  
  String currentRoomId = '';

  // Module manager for accessing LoginModule
  final ModuleManager _moduleManager = ModuleManager();

  @override
  void initState() {
    super.initState();
    _initializeSocket();
  }

  void _initializeSocket() async {
    log.info('🔌 Initializing WebSocket connection to external app...');
    
    // Get JWT token from login module for authentication
    final loginModule = _moduleManager.getModuleByType<LoginModule>();
    if (loginModule == null) {
      log.error('❌ Login module not available for WebSocket authentication');
      setState(() {
        messages.add('❌ Login module not available');
      });
      return;
    }
    
    // Check if user has valid JWT token
    final hasToken = await loginModule.hasValidToken();
    if (!hasToken) {
      log.error('❌ No valid JWT token available for WebSocket authentication');
      setState(() {
        messages.add('❌ Please login first to get JWT token for WebSocket authentication');
      });
      return;
    }
    
    // Get the JWT token
    final authToken = await loginModule.getCurrentToken();
    if (authToken == null) {
      log.error('❌ Failed to retrieve JWT token for WebSocket authentication');
      setState(() {
        messages.add('❌ Failed to get authentication token');
      });
      return;
    }
    
    log.info('✅ Using JWT token for WebSocket authentication');
    
    // Connect to the external app WebSocket server with JWT token
    socket = IO.io(Config.wsUrl, <String, dynamic>{
      'transports': ['websocket'],
      'autoConnect': false, // Don't auto-connect
      'query': {
        'token': authToken, // Use the JWT token for authentication
        'client_id': 'flutter_app_${DateTime.now().millisecondsSinceEpoch}', // Add unique client ID
        'version': '1.0.0', // Add version info
      },
      'auth': {
        'token': authToken, // Also send in auth object
      },
    });

    // Set up event listeners
    socket!.onConnect((_) {
      log.info('✅ WebSocket connected successfully with JWT authentication');
      setState(() {
        isConnected = true;
        connectionStatus = 'Connected';
        sessionId = socket!.id;
        messages.add('✅ Connected to WebSocket server with JWT authentication (ID: ${socket!.id})');
      });
      
      // Request session data after connection
      socket!.emit('get_session_data', {
        'client_id': 'flutter_app_${DateTime.now().millisecondsSinceEpoch}',
      });
    });

    socket!.onDisconnect((_) {
      log.info('❌ WebSocket disconnected');
      setState(() {
        isConnected = false;
        connectionStatus = 'Disconnected';
        sessionId = null;
        messages.add('❌ Disconnected from WebSocket server');
      });
    });

    socket!.onConnectError((error) {
      log.error('🚨 WebSocket connection error: $error');
      setState(() {
        isConnected = false;
        connectionStatus = 'Connection Error';
        sessionId = null;
        messages.add('🚨 Connection error: $error');
      });
    });

    socket!.on('session_data', (data) {
      log.info('📋 Received session data from WebSocket server');
      setState(() {
        sessionData = Map<String, dynamic>.from(data);
        messages.add('📋 Received session data: ${json.encode(data)}');
      });
    });

    socket!.on('join_room_success', (data) {
      log.info('🏠 Successfully joined WebSocket room');
      setState(() {
        currentRoomId = data['room_id'] ?? '';
        messages.add('🏠 Successfully joined room: ${json.encode(data)}');
      });
    });

    socket!.on('join_room_error', (data) {
      log.error('🚨 Failed to join WebSocket room: ${json.encode(data)}');
      setState(() {
        messages.add('🚨 Failed to join room: ${json.encode(data)}');
      });
    });

    socket!.on('room_state', (data) {
      log.debug('📊 Received room state update');
      setState(() {
        messages.add('📊 Room state update: ${json.encode(data)}');
      });
    });

    socket!.on('message', (data) {
      log.info('💬 Received WebSocket message');
      setState(() {
        messages.add('💬 Received message: ${json.encode(data)}');
      });
    });

    socket!.on('error', (data) {
      log.error('🚨 WebSocket error: ${json.encode(data)}');
      setState(() {
        messages.add('🚨 Error: ${json.encode(data)}');
      });
    });
    
    // Add authentication event listener
    socket!.on('auth_required', (data) {
      log.info('🔐 Authentication required');
      setState(() {
        messages.add('🔐 Authentication required: ${json.encode(data)}');
      });
    });
    
    socket!.on('auth_success', (data) {
      log.info('✅ Authentication successful');
      setState(() {
        messages.add('✅ Authentication successful: ${json.encode(data)}');
      });
    });
  }

  void _connect() {
    if (socket != null && !isConnected) {
      log.info('🚀 Attempting to connect to WebSocket server...');
      socket!.connect();
    }
  }

  void _disconnect() {
    log.info('🔌 Manually disconnecting WebSocket...');
    socket?.disconnect();
  }

  void _joinRoom() {
    final roomId = _roomIdController.text.trim();
    if (roomId.isEmpty) {
      messages.add('⚠️ Please enter a room ID');
      return;
    }
    
    if (socket != null && isConnected) {
      log.info('🏠 Attempting to join room: $roomId');
      socket!.emit('join_room', {'room_id': roomId});
      messages.add('🏠 Attempting to join room: $roomId');
    } else {
      log.error('🚨 Cannot join room: WebSocket not connected');
      messages.add('🚨 Cannot join room: WebSocket not connected');
    }
  }

  void _sendMessage() {
    final message = _customMessageController.text.trim();
    if (message.isEmpty) {
      messages.add('⚠️ Please enter a message');
      return;
    }
    
    if (socket != null && isConnected) {
      log.info('💬 Sending WebSocket message: $message');
      socket!.emit('message', {
        'room_id': currentRoomId.isNotEmpty ? currentRoomId : 'test_room',
        'message': message,
      });
      messages.add('💬 Sent message: $message');
      _customMessageController.clear(); // Clear the input
    } else {
      log.error('🚨 Cannot send message: WebSocket not connected');
      messages.add('🚨 Cannot send message: WebSocket not connected');
    }
  }

  void _sendTestMessage() {
    final message = _messageController.text.trim();
    if (message.isEmpty) {
      messages.add('⚠️ Please enter a test message');
      return;
    }
    
    if (socket != null && isConnected) {
      log.info('💬 Sending test message: $message');
      socket!.emit('message', {
        'room_id': currentRoomId.isNotEmpty ? currentRoomId : 'test_room',
        'message': message,
      });
      messages.add('💬 Sent test message: $message');
      _messageController.clear(); // Clear the input
    } else {
      log.error('🚨 Cannot send message: WebSocket not connected');
      messages.add('🚨 Cannot send message: WebSocket not connected');
    }
  }

  void _clearMessages() {
    log.info('🧹 Clearing message log');
    setState(() {
      messages.clear();
    });
  }

  @override
  void dispose() {
    log.info('🔌 Disposing WebSocket connection');
    socket?.disconnect();
    socket?.dispose();
    _roomIdController.dispose();
    _messageController.dispose();
    _customMessageController.dispose();
    super.dispose();
  }

  @override
  Widget buildContent(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        children: [
          // Connection Status
          Container(
            padding: const EdgeInsets.all(16),
            color: isConnected ? Colors.green : Colors.red,
            child: Row(
              children: [
                Icon(
                  isConnected ? Icons.wifi : Icons.wifi_off,
                  color: Colors.white,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    connectionStatus,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                if (sessionId != null)
                  Text(
                    'ID: ${sessionId!.substring(0, 8)}...',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                    ),
                  ),
              ],
            ),
          ),

          // Session Data Display
          if (sessionData != null)
            Container(
              padding: const EdgeInsets.all(16),
              margin: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.blue.shade200),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Session Data:',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    json.encode(sessionData),
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),

          // Connection Controls
          Container(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                // Connect/Disconnect Button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: isConnected ? _disconnect : _connect,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isConnected ? Colors.red : Colors.green,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                    child: Text(
                      isConnected ? 'Disconnect' : 'Connect',
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
                
                const SizedBox(height: 16),
                
                // Room Management
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.orange.shade200),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Room Management',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _roomIdController,
                              decoration: const InputDecoration(
                                labelText: 'Room ID',
                                hintText: 'Enter room ID to join',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: isConnected ? _joinRoom : null,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.orange,
                              foregroundColor: Colors.white,
                            ),
                            child: const Text('Join Room'),
                          ),
                        ],
                      ),
                      if (currentRoomId.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            'Current Room: $currentRoomId',
                            style: const TextStyle(
                              color: Colors.orange,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                
                const SizedBox(height: 16),
                
                // Message Sending
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.green.shade200),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Send Messages',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _customMessageController,
                              decoration: const InputDecoration(
                                labelText: 'Custom Message',
                                hintText: 'Enter your message',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: isConnected ? _sendMessage : null,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.green,
                              foregroundColor: Colors.white,
                            ),
                            child: const Text('Send'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _messageController,
                              decoration: const InputDecoration(
                                labelText: 'Test Message',
                                hintText: 'Quick test message',
                                border: OutlineInputBorder(),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: isConnected ? _sendTestMessage : null,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.blue,
                              foregroundColor: Colors.white,
                            ),
                            child: const Text('Send Test'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Clear Messages Button
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: _clearMessages,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.grey,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Clear Messages'),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Messages List
          Container(
            height: 300,
            margin: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey.shade300),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(8),
                      topRight: Radius.circular(8),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.message),
                      const SizedBox(width: 8),
                      const Text(
                        'WebSocket Messages',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const Spacer(),
                      Text(
                        '${messages.length} messages',
                        style: const TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.all(8),
                    itemCount: messages.length,
                    itemBuilder: (context, index) {
                      final message = messages[index];
                      Color messageColor = Colors.grey.shade50;
                      
                      // Color code messages based on type
                      if (message.contains('✅')) messageColor = Colors.green.shade50;
                      else if (message.contains('❌') || message.contains('🚨')) messageColor = Colors.red.shade50;
                      else if (message.contains('🏠')) messageColor = Colors.orange.shade50;
                      else if (message.contains('💬')) messageColor = Colors.blue.shade50;
                      
                      return Container(
                        margin: const EdgeInsets.only(bottom: 4),
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: messageColor,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          message,
                          style: const TextStyle(fontSize: 12),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
} 