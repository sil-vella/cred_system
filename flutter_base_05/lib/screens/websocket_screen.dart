import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:convert';
import '../core/00_base/screen_base.dart';
import '../utils/consts/config.dart';
import '../modules/login_module/login_module.dart';
import '../core/managers/module_manager.dart';
import '../core/managers/websocket_manager.dart';

class WebSocketScreen extends BaseScreen {
  const WebSocketScreen({Key? key}) : super(key: key);

  @override
  String computeTitle(BuildContext context) => 'WebSocket Test';

  @override
  BaseScreenState<WebSocketScreen> createState() => _WebSocketScreenState();
}

class _WebSocketScreenState extends BaseScreenState<WebSocketScreen> {
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
  
  // WebSocket manager from provider
  WebSocketManager? _websocketManager;

  @override
  void initState() {
    super.initState();
    _initializeSocket();
  }

  void _initializeSocket() async {
    log.info('🔌 Initializing WebSocket connection to external app...');
    
    // Get the WebSocket manager from provider
    _websocketManager = Provider.of<WebSocketManager>(context, listen: false);
    
    // Check if already connected
    if (_websocketManager!.isConnected) {
      log.info('✅ WebSocket already connected');
      setState(() {
        isConnected = true;
        connectionStatus = 'Connected';
        messages.add('✅ WebSocket already connected');
      });
      return;
    }
    
    // Try to connect using the WebSocket manager
    log.info('🔄 Connecting to WebSocket server...');
    final success = await _websocketManager!.connect(context);
    
    if (success) {
      log.info('✅ WebSocket connected successfully');
      setState(() {
        isConnected = true;
        connectionStatus = 'Connected';
        messages.add('✅ WebSocket connected successfully');
      });
    } else {
      log.error('❌ WebSocket connection failed');
      setState(() {
        isConnected = false;
        connectionStatus = 'Connection Failed';
        messages.add('❌ WebSocket connection failed');
      });
    }

    // Note: Event listeners are handled by the WebSocketManager
    // The WebSocketManager will handle all the Socket.IO events internally
  }

  void _connect() async {
    // Ensure WebSocketManager is initialized
    if (_websocketManager == null) {
      log.info('🔄 WebSocketManager is null - reinitializing...');
      _websocketManager = Provider.of<WebSocketManager>(context, listen: false);
    }
    
    if (_websocketManager != null && !isConnected) {
      log.info('🚀 Attempting to connect to WebSocket server...');
      final success = await _websocketManager!.connect(context);
      if (success) {
        setState(() {
          isConnected = true;
          connectionStatus = 'Connected';
          messages.add('✅ Connected to WebSocket server');
        });
      } else {
        setState(() {
          isConnected = false;
          connectionStatus = 'Connection Failed';
          messages.add('❌ Failed to connect to WebSocket server');
        });
      }
    }
  }

  void _disconnect() {
    log.info('🔌 Manually disconnecting WebSocket...');
    _websocketManager?.disconnect();
    setState(() {
      isConnected = false;
      connectionStatus = 'Disconnected';
      messages.add('🔌 Disconnected from WebSocket server');
    });
  }

  void _joinRoom() async {
    final roomId = _roomIdController.text.trim();
    if (roomId.isEmpty) {
      messages.add('⚠️ Please enter a room ID');
      return;
    }
    
    // Ensure WebSocketManager is initialized
    if (_websocketManager == null) {
      log.info('🔄 WebSocketManager is null - reinitializing...');
      _websocketManager = Provider.of<WebSocketManager>(context, listen: false);
    }
    
    if (_websocketManager != null && isConnected) {
      log.info('🏠 Attempting to join room: $roomId');
      final result = await _websocketManager!.joinRoom(roomId);
      if (result['success'] != null) {
        messages.add('🏠 Successfully joined room: $roomId');
        setState(() {
          currentRoomId = roomId;
        });
      } else {
        messages.add('🚨 Failed to join room: ${result['error']}');
      }
    } else {
      log.error('🚨 Cannot join room: WebSocket not connected');
      messages.add('🚨 Cannot join room: WebSocket not connected');
    }
  }

  void _sendMessage() async {
    final message = _customMessageController.text.trim();
    if (message.isEmpty) {
      messages.add('⚠️ Please enter a message');
      return;
    }
    
    // Ensure WebSocketManager is initialized
    if (_websocketManager == null) {
      log.info('🔄 WebSocketManager is null - reinitializing...');
      _websocketManager = Provider.of<WebSocketManager>(context, listen: false);
    }
    
    if (_websocketManager != null && isConnected) {
      log.info('💬 Sending WebSocket message: $message');
      final result = await _websocketManager!.sendMessage(message);
      if (result['success'] != null) {
        messages.add('💬 Sent message: $message');
        _customMessageController.clear(); // Clear the input
      } else {
        messages.add('🚨 Failed to send message: ${result['error']}');
      }
    } else {
      log.error('🚨 Cannot send message: WebSocket not connected');
      messages.add('🚨 Cannot send message: WebSocket not connected');
    }
  }

  void _sendTestMessage() async {
    final message = _messageController.text.trim();
    if (message.isEmpty) {
      messages.add('⚠️ Please enter a test message');
      return;
    }
    
    // Ensure WebSocketManager is initialized
    if (_websocketManager == null) {
      log.info('🔄 WebSocketManager is null - reinitializing...');
      _websocketManager = Provider.of<WebSocketManager>(context, listen: false);
    }
    
    if (_websocketManager != null && isConnected) {
      log.info('💬 Sending test message: $message');
      final result = await _websocketManager!.sendMessage(message);
      if (result['success'] != null) {
        messages.add('💬 Sent test message: $message');
        _messageController.clear(); // Clear the input
      } else {
        messages.add('🚨 Failed to send test message: ${result['error']}');
      }
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
    log.info('🔌 Disposing WebSocket screen (keeping connection alive)');
    // Don't disconnect the WebSocket manager - keep it alive for other screens
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