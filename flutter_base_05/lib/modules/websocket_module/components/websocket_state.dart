import 'dart:convert';

class WebSocketState {
  // Connection State
  final bool isConnected;
  final String? sessionId;
  final String? userId;
  final String? username;
  
  // Room State
  final String? currentRoomId;
  final Map<String, dynamic>? roomState;
  final List<String> joinedRooms;
  
  // Session State
  final Map<String, dynamic>? sessionData;
  final DateTime? lastActivity;
  final DateTime? connectionTime;
  
  // Error State
  final String? error;
  final bool isLoading;

  WebSocketState({
    this.isConnected = false,
    this.sessionId,
    this.userId,
    this.username,
    this.currentRoomId,
    this.roomState,
    this.joinedRooms = const [],
    this.sessionData,
    this.lastActivity,
    this.connectionTime,
    this.error,
    this.isLoading = false,
  });

  WebSocketState copyWith({
    bool? isConnected,
    String? sessionId,
    String? userId,
    String? username,
    String? currentRoomId,
    Map<String, dynamic>? roomState,
    List<String>? joinedRooms,
    Map<String, dynamic>? sessionData,
    DateTime? lastActivity,
    DateTime? connectionTime,
    String? error,
    bool? isLoading,
  }) {
    return WebSocketState(
      isConnected: isConnected ?? this.isConnected,
      sessionId: sessionId ?? this.sessionId,
      userId: userId ?? this.userId,
      username: username ?? this.username,
      currentRoomId: currentRoomId ?? this.currentRoomId,
      roomState: roomState ?? this.roomState,
      joinedRooms: joinedRooms ?? this.joinedRooms,
      sessionData: sessionData ?? this.sessionData,
      lastActivity: lastActivity ?? this.lastActivity,
      connectionTime: connectionTime ?? this.connectionTime,
      error: error ?? this.error,
      isLoading: isLoading ?? this.isLoading,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'isConnected': isConnected,
      'sessionId': sessionId,
      'userId': userId,
      'username': username,
      'currentRoomId': currentRoomId,
      'roomState': roomState,
      'joinedRooms': joinedRooms,
      'sessionData': sessionData,
      'lastActivity': lastActivity?.toIso8601String(),
      'connectionTime': connectionTime?.toIso8601String(),
      'error': error,
      'isLoading': isLoading,
    };
  }

  factory WebSocketState.fromJson(Map<String, dynamic> json) {
    return WebSocketState(
      isConnected: json['isConnected'] ?? false,
      sessionId: json['sessionId'],
      userId: json['userId'],
      username: json['username'],
      currentRoomId: json['currentRoomId'],
      roomState: json['roomState'],
      joinedRooms: List<String>.from(json['joinedRooms'] ?? []),
      sessionData: json['sessionData'],
      lastActivity: json['lastActivity'] != null ? DateTime.parse(json['lastActivity']) : null,
      connectionTime: json['connectionTime'] != null ? DateTime.parse(json['connectionTime']) : null,
      error: json['error'],
      isLoading: json['isLoading'] ?? false,
    );
  }
} 