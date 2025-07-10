import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'dart:convert';
import '../core/00_base/screen_base.dart';
import '../utils/consts/config.dart';

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

  @override
  void initState() {
    super.initState();
    _initializeSocket();
  }

  void _initializeSocket() {
    log.info('🔌 Initializing WebSocket connection to external app...');
    
    // Connect to the external app WebSocket server
    socket = IO.io(Config.wsUrl, <String, dynamic>{
      'transports': ['websocket'],
      'autoConnect': false,
      'query': {
        'token': 'test_token_123', // You'll need a real JWT token here
      },
    });

    // Set up event listeners
    socket!.onConnect((_) {
      log.info('✅ WebSocket connected successfully');
      setState(() {
        isConnected = true;
        connectionStatus = 'Connected';
        messages.add('Connected to WebSocket server');
      });
    });

    socket!.onDisconnect((_) {
      log.info('❌ WebSocket disconnected');
      setState(() {
        isConnected = false;
        connectionStatus = 'Disconnected';
        messages.add('Disconnected from WebSocket server');
      });
    });

    socket!.onConnectError((error) {
      log.error('🚨 WebSocket connection error: $error');
      setState(() {
        isConnected = false;
        connectionStatus = 'Connection Error';
        messages.add('Connection error: $error');
      });
    });

    socket!.on('session_data', (data) {
      log.info('📋 Received session data from WebSocket server');
      setState(() {
        sessionData = Map<String, dynamic>.from(data);
        messages.add('Received session data: ${json.encode(data)}');
      });
    });

    socket!.on('join_room_success', (data) {
      log.info('🏠 Successfully joined WebSocket room');
      setState(() {
        messages.add('Joined room: ${json.encode(data)}');
      });
    });

    socket!.on('join_room_error', (data) {
      log.error('🚨 Failed to join WebSocket room: ${json.encode(data)}');
      setState(() {
        messages.add('Join room error: ${json.encode(data)}');
      });
    });

    socket!.on('room_state', (data) {
      log.debug('📊 Received room state update');
      setState(() {
        messages.add('Room state: ${json.encode(data)}');
      });
    });

    socket!.on('message', (data) {
      log.info('💬 Received WebSocket message');
      setState(() {
        messages.add('Message: ${json.encode(data)}');
      });
    });

    socket!.on('error', (data) {
      log.error('🚨 WebSocket error: ${json.encode(data)}');
      setState(() {
        messages.add('Error: ${json.encode(data)}');
      });
    });

    // Connect to the server
    log.info('🚀 Attempting to connect to WebSocket server...');
    socket!.connect();
  }

  void _disconnect() {
    log.info('🔌 Manually disconnecting WebSocket...');
    socket?.disconnect();
  }

  void _joinRoom(String roomId) {
    if (socket != null && isConnected) {
      log.info('🏠 Attempting to join room: $roomId');
      socket!.emit('join_room', {'room_id': roomId});
      messages.add('Attempting to join room: $roomId');
    } else {
      log.error('🚨 Cannot join room: WebSocket not connected');
    }
  }

  void _sendMessage(String message) {
    if (socket != null && isConnected) {
      log.info('💬 Sending WebSocket message: $message');
      socket!.emit('message', {
        'room_id': 'test_room',
        'message': message,
      });
      messages.add('Sent message: $message');
    } else {
      log.error('🚨 Cannot send message: WebSocket not connected');
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
                Text(
                  connectionStatus,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
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

          // Control Buttons
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: isConnected ? _disconnect : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Disconnect'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: isConnected ? () => _joinRoom('test_room') : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.orange,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Join Room'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: isConnected ? () => _sendMessage('Hello from Flutter!') : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Send Message'),
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
            height: 300, // Fixed height instead of Expanded
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
                  child: const Row(
                    children: [
                      Icon(Icons.message),
                      SizedBox(width: 8),
                      Text(
                        'WebSocket Messages',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.all(8),
                    itemCount: messages.length,
                    itemBuilder: (context, index) {
                      return Container(
                        margin: const EdgeInsets.only(bottom: 4),
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: Colors.grey.shade50,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          messages[index],
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