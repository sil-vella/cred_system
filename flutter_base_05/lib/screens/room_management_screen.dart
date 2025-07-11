import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:provider/provider.dart';
import 'dart:convert';
import 'dart:async';
import '../core/00_base/screen_base.dart';
import '../core/managers/websocket_manager.dart';
import '../core/managers/state_manager.dart';

class RoomManagementScreen extends BaseScreen {
  const RoomManagementScreen({Key? key}) : super(key: key);

  @override
  String computeTitle(BuildContext context) => 'Room Management';

  @override
  BaseScreenState<RoomManagementScreen> createState() => _RoomManagementScreenState();
}

class _RoomManagementScreenState extends BaseScreenState<RoomManagementScreen> {
  
  // Controllers
  final TextEditingController _roomNameController = TextEditingController();
  final TextEditingController _roomIdController = TextEditingController();
  final TextEditingController _allowedUsersController = TextEditingController();
  final TextEditingController _allowedRolesController = TextEditingController();
  
  // State variables
  String _selectedPermission = 'public';
  List<Map<String, dynamic>> _publicRooms = [];
  List<Map<String, dynamic>> _myRooms = [];
  bool _isLoading = false;
  String _currentRoomId = '';
  Map<String, dynamic>? _currentRoomInfo;
  
  // WebSocket manager
  WebSocketManager? _websocketManager;
  
  // Permission options
  final List<String> _permissionOptions = [
    'public',
    'private', 
    'restricted',
    'owner_only'
  ];

  @override
  void initState() {
    super.initState();
    _initializeWebSocket().then((_) {
      _loadPublicRooms();
    });
  }

  Future<void> _initializeWebSocket() async {
    try {
      // Get the WebSocket manager from provider
      _websocketManager = Provider.of<WebSocketManager>(context, listen: false);
      
      // Check if WebSocketManager is already connected
      if (_websocketManager!.isConnected) {
        log.info("✅ WebSocket already connected");
        return;
      }
      
      // Check StateManager for existing connection
      final stateManager = Provider.of<StateManager>(context, listen: false);
      final websocketState = stateManager.getPluginState<Map<String, dynamic>>("websocket");
      
      if (websocketState != null && websocketState['isConnected'] == true) {
        log.info("✅ Using existing WebSocket connection from StateManager");
        return;
      }
      
      // Only try to connect if no existing connection
      log.info("🔄 No existing connection found, connecting to WebSocket server...");
      final success = await _websocketManager!.connect(context);
      
      if (success) {
        log.info("✅ WebSocket connected successfully");
      } else {
        log.error("❌ WebSocket connection failed");
        // Don't show error snackbar - user might already be connected from another screen
        log.info("ℹ️ Assuming WebSocket is already connected from another screen");
      }
    } catch (e) {
      log.error("❌ Error initializing WebSocket: $e");
      // Don't show error snackbar - user might already be connected from another screen
      log.info("ℹ️ Assuming WebSocket is already connected from another screen");
    }
  }

  @override
  void dispose() {
    _roomNameController.dispose();
    _roomIdController.dispose();
    _allowedUsersController.dispose();
    _allowedRolesController.dispose();
    super.dispose();
  }

  Future<void> _loadPublicRooms() async {
    setState(() {
      _isLoading = true;
    });

    try {
      // For now, we'll simulate some rooms since we need to implement room discovery
      // In a real implementation, this would come from WebSocket events
      await Future.delayed(const Duration(seconds: 1));
      
      setState(() {
        _publicRooms = [
          {
            'room_id': 'demo-room-1',
            'owner_id': 'user123',
            'permission': 'public',
            'current_size': 2,
            'max_size': 10,
            'created_at': '2024-01-15T10:30:00Z'
          },
          {
            'room_id': 'demo-room-2', 
            'owner_id': 'user456',
            'permission': 'public',
            'current_size': 1,
            'max_size': 10,
            'created_at': '2024-01-15T11:00:00Z'
          }
        ];
        _isLoading = false;
      });
    } catch (e) {
      log.error("Error loading public rooms: $e");
      setState(() {
        _isLoading = false;
      });
      _showSnackBar('Failed to load public rooms: $e', isError: true);
    }
  }

  Future<void> _createRoom() async {
    if (_roomNameController.text.trim().isEmpty) {
      _showSnackBar('Please enter a room name', isError: true);
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      // Prepare room data based on permission type
      Map<String, dynamic> roomData = {
        'permission': _selectedPermission,
      };

      // Only add allowed users/roles for non-public rooms
      if (_selectedPermission != 'public') {
        List<String> allowedUsers = [];
        List<String> allowedRoles = [];
        
        if (_allowedUsersController.text.isNotEmpty) {
          allowedUsers = _allowedUsersController.text.split(',').map((e) => e.trim()).toList();
        }
        
        if (_allowedRolesController.text.isNotEmpty) {
          allowedRoles = _allowedRolesController.text.split(',').map((e) => e.trim()).toList();
        }
        
        roomData['allowed_users'] = allowedUsers;
        roomData['allowed_roles'] = allowedRoles;
      }

      // Create room via WebSocket manager
      log.info("🏠 Attempting to create room with data: $roomData");
      
      if (_websocketManager == null) {
        log.error("❌ WebSocketManager is null - reinitializing...");
        _websocketManager = Provider.of<WebSocketManager>(context, listen: false);
      }
      
      final result = await _websocketManager?.createRoom('current_user', roomData);
      
      log.info("🏠 Create room result: $result");
      
      if (result?['success'] != null && result!['success'].toString().contains('successfully')) {
        // Use the actual room data from the server response
        final roomData = result!['data'] as Map<String, dynamic>;
        final newRoom = {
          'room_id': roomData['room_id'],
          'owner_id': 'current_user',
          'permission': _selectedPermission,
          'current_size': roomData['current_size'],
          'max_size': roomData['max_size'],
          'created_at': DateTime.now().toIso8601String(),
          'allowed_users': roomData['allowed_users'] ?? [],
          'allowed_roles': roomData['allowed_roles'] ?? [],
        };

        setState(() {
          _myRooms.add(newRoom);
          _isLoading = false;
        });

        _showSnackBar('Room created successfully!');
        _clearForm();
      } else {
        throw Exception(result?['error'] ?? 'Failed to create room');
      }
      
    } catch (e) {
      log.error("Error creating room: $e");
      setState(() {
        _isLoading = false;
      });
      _showSnackBar('Failed to create room: $e', isError: true);
    }
  }

  Future<void> _joinRoom(String roomId) async {
    setState(() {
      _isLoading = true;
    });

    try {
      // Join room via WebSocket manager
      log.info("🚪 Joining room: $roomId");
      final result = await _websocketManager?.joinRoom(roomId);
      
      if (result?['success'] == true) {
        setState(() {
          _currentRoomId = roomId;
          _currentRoomInfo = {
            'room_id': roomId,
            'owner_id': 'user123',
            'permission': 'public',
            'current_size': 3,
            'max_size': 10,
            'created_at': '2024-01-15T10:30:00Z',
            'members': ['user123', 'user456', 'current_user'],
            'allowed_users': [],
            'allowed_roles': []
          };
          _isLoading = false;
        });

        _showSnackBar('Joined room: $roomId');
      } else {
        throw Exception(result?['error'] ?? 'Failed to join room');
      }
      
    } catch (e) {
      log.error("Error joining room: $e");
      setState(() {
        _isLoading = false;
      });
      _showSnackBar('Failed to join room: $e', isError: true);
    }
  }

  Future<void> _leaveRoom(String roomId) async {
    try {
      // Leave room via WebSocket manager
      log.info("🚪 Leaving room: $roomId");
      final result = await _websocketManager?.leaveRoom(roomId);
      
      if (result?['success'] == true) {
        setState(() {
          if (_currentRoomId == roomId) {
            _currentRoomId = '';
            _currentRoomInfo = null;
          }
        });

        _showSnackBar('Left room: $roomId');
      } else {
        throw Exception(result?['error'] ?? 'Failed to leave room');
      }
      
    } catch (e) {
      log.error("Error leaving room: $e");
      _showSnackBar('Failed to leave room: $e', isError: true);
    }
  }

  Future<void> _deleteRoom(String roomId) async {
    // Show confirmation dialog
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Room'),
        content: Text('Are you sure you want to delete room "$roomId"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete'),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      // For now, we'll simulate room deletion
      // In a real implementation, this would be a WebSocket event
      setState(() {
        _myRooms.removeWhere((room) => room['room_id'] == roomId);
        if (_currentRoomId == roomId) {
          _currentRoomId = '';
          _currentRoomInfo = null;
        }
      });

      _showSnackBar('Room deleted successfully');
      
    } catch (e) {
      log.error("Error deleting room: $e");
      _showSnackBar('Failed to delete room: $e', isError: true);
    }
  }

  Future<void> _updateRoomPermissions(String roomId) async {
    String? newPermission;
    List<String> allowedUsers = [];
    List<String> allowedRoles = [];

    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Update Room Permissions'),
        content: StatefulBuilder(
          builder: (context, setState) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                value: newPermission ?? 'public',
                decoration: const InputDecoration(labelText: 'Permission'),
                items: _permissionOptions.map((p) => DropdownMenuItem(value: p, child: Text(p))).toList(),
                onChanged: (value) => setState(() => newPermission = value),
              ),
              const SizedBox(height: 16),
              if (newPermission != null && newPermission != 'public') ...[
                TextField(
                  decoration: const InputDecoration(
                    labelText: 'Allowed Users (comma-separated)',
                    hintText: 'user1, user2, user3',
                  ),
                  onChanged: (value) => allowedUsers = value.split(',').map((e) => e.trim()).toList(),
                ),
                const SizedBox(height: 16),
                TextField(
                  decoration: const InputDecoration(
                    labelText: 'Allowed Roles (comma-separated)',
                    hintText: 'admin, moderator, user',
                  ),
                  onChanged: (value) => allowedRoles = value.split(',').map((e) => e.trim()).toList(),
                ),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(null),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop({
              'permission': newPermission,
              'allowed_users': allowedUsers,
              'allowed_roles': allowedRoles,
            }),
            child: const Text('Update'),
          ),
        ],
      ),
    );

    if (result == null) return;

    try {
      // For now, we'll simulate permission update
      // In a real implementation, this would be a WebSocket event
      _showSnackBar('Room permissions updated successfully');
      
    } catch (e) {
      log.error("Error updating room permissions: $e");
      _showSnackBar('Failed to update room permissions: $e', isError: true);
    }
  }

  void _clearForm() {
    _roomNameController.clear();
    _roomIdController.clear();
    _allowedUsersController.clear();
    _allowedRolesController.clear();
    setState(() {
      _selectedPermission = 'public';
    });
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red : Colors.green,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  @override
  Widget buildContent(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Create Room Section
          _buildCreateRoomSection(),
          const SizedBox(height: 24),
          // Current Room Info
          if (_currentRoomInfo != null) _buildCurrentRoomSection(),
          const SizedBox(height: 24),
          // Public Rooms Section
          _buildPublicRoomsSection(),
          const SizedBox(height: 24),
          // My Rooms Section
          _buildMyRoomsSection(),
        ],
      ),
    );
  }

  Widget _buildCreateRoomSection() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Create New Room',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            
            // Room Name
            TextField(
              controller: _roomNameController,
              decoration: const InputDecoration(
                labelText: 'Room Name',
                border: OutlineInputBorder(),
                hintText: 'Enter room name',
              ),
            ),
            const SizedBox(height: 16),
            
            // Permission Dropdown
            DropdownButtonFormField<String>(
              value: _selectedPermission,
              decoration: const InputDecoration(
                labelText: 'Permission',
                border: OutlineInputBorder(),
              ),
              items: _permissionOptions.map((String permission) {
                return DropdownMenuItem<String>(
                  value: permission,
                  child: Text(permission.toUpperCase()),
                );
              }).toList(),
              onChanged: (String? newValue) {
                setState(() {
                  _selectedPermission = newValue!;
                });
              },
            ),
            const SizedBox(height: 16),
            
            // Conditional fields for non-public rooms
            if (_selectedPermission != 'public') ...[
              TextField(
                controller: _allowedUsersController,
                decoration: const InputDecoration(
                  labelText: 'Allowed Users (comma-separated)',
                  border: OutlineInputBorder(),
                  hintText: 'user1, user2, user3',
                ),
              ),
              const SizedBox(height: 16),
              
              TextField(
                controller: _allowedRolesController,
                decoration: const InputDecoration(
                  labelText: 'Allowed Roles (comma-separated)',
                  border: OutlineInputBorder(),
                  hintText: 'admin, moderator, user',
                ),
              ),
              const SizedBox(height: 16),
            ],
            
            // Create Button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _createRoom,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: const Text(
                  'Create Room',
                  style: TextStyle(fontSize: 16),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCurrentRoomSection() {
    return Card(
      elevation: 4,
      color: Colors.green.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.room, color: Colors.green),
                const SizedBox(width: 8),
                const Text(
                  'Current Room',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                IconButton(
                  onPressed: () {
                    setState(() {
                      _currentRoomInfo = null;
                      _currentRoomId = '';
                    });
                  },
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text('Room ID: ${_currentRoomInfo!['room_id']}'),
            Text('Owner: ${_currentRoomInfo!['owner_id']}'),
            Text('Permission: ${_currentRoomInfo!['permission']}'),
            Text('Members: ${_currentRoomInfo!['current_size']}/${_currentRoomInfo!['max_size']}'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                Chip(
                  label: Text('Members: ${_currentRoomInfo!['members'].length}'),
                  backgroundColor: Colors.blue.shade100,
                ),
                Chip(
                  label: Text('Permission: ${_currentRoomInfo!['permission']}'),
                  backgroundColor: Colors.green.shade100,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPublicRoomsSection() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.public),
                const SizedBox(width: 8),
                const Text(
                  'Public Rooms',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                IconButton(
                  onPressed: _loadPublicRooms,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (_publicRooms.isEmpty)
              const Center(
                child: Text(
                  'No public rooms available',
                  style: TextStyle(color: Colors.grey),
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _publicRooms.length,
                itemBuilder: (context, index) {
                  final room = _publicRooms[index];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: const Icon(Icons.room),
                      title: Text(room['room_id']),
                      subtitle: Text(
                        '${room['current_size']}/${room['max_size']} members • ${room['permission']}',
                      ),
                      trailing: ElevatedButton(
                        onPressed: () => _joinRoom(room['room_id']),
                        child: const Text('Join'),
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildMyRoomsSection() {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.person),
                const SizedBox(width: 8),
                const Text(
                  'My Rooms',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                IconButton(
                  onPressed: () {
                    // Refresh my rooms
                  },
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (_myRooms.isEmpty)
              const Center(
                child: Text(
                  'You haven\'t created any rooms yet',
                  style: TextStyle(color: Colors.grey),
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _myRooms.length,
                itemBuilder: (context, index) {
                  final room = _myRooms[index];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: const Icon(Icons.room),
                      title: Text(room['room_id']),
                      subtitle: Text(
                        '${room['current_size']}/${room['max_size']} members • ${room['permission']}',
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            onPressed: () => _joinRoom(room['room_id']),
                            icon: const Icon(Icons.login),
                            tooltip: 'Join',
                          ),
                          IconButton(
                            onPressed: () {
                              // Edit room
                            },
                            icon: const Icon(Icons.edit),
                            tooltip: 'Edit',
                          ),
                          IconButton(
                            onPressed: () {
                              // Delete room
                            },
                            icon: const Icon(Icons.delete),
                            tooltip: 'Delete',
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
} 