import '../../../../../../tools/logging/logger.dart';

class SessionManager {
  static final Logger _log = Logger();
  Map<String, dynamic>? _sessionData;

  Map<String, dynamic>? get sessionData => _sessionData;

  void updateSessionData(Map<String, dynamic> data) {
    _sessionData = data;
    _log.info("✅ Session data updated");
  }

  void clearSessionData() {
    _sessionData = null;
    _log.info("✅ Session data cleared");
  }

  void setUserId(String userId) {
    if (_sessionData == null) {
      _sessionData = <String, dynamic>{};
    }
    _sessionData!['user_id'] = userId;
    _log.info("✅ User ID set to: $userId");
  }

  void setUsername(String? username) {
    if (_sessionData == null) {
      _sessionData = <String, dynamic>{};
    }
    _sessionData!['username'] = username;
    _log.info("✅ Username set to: $username");
  }

  bool isInRoom(String roomId) {
    if (_sessionData == null) return false;
    final rooms = _sessionData!['rooms'] as List?;
    return rooms?.contains(roomId) ?? false;
  }

  List<String> getRooms() {
    if (_sessionData == null) return [];
    final rooms = _sessionData!['rooms'] as List?;
    return rooms?.cast<String>() ?? [];
  }

  String? getUserId() {
    return _sessionData?['user_id'] as String?;
  }

  String? getUsername() {
    return _sessionData?['username'] as String?;
  }
} 