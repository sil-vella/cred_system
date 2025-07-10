import 'dart:convert';
import 'dart:async';
import '../../../../../tools/logging/logger.dart';
import '../../connections_api_module/connections_api_module.dart';
import '../../../../../core/managers/state_manager.dart';

class TokenManager {
  static final Logger _log = Logger();
  final ConnectionsApiModule? _connectionModule;
  StateManager? _stateManager;
  String? _currentToken;
  Timer? _tokenRefreshTimer;

  TokenManager(this._connectionModule);

  void setStateManager(StateManager stateManager) {
    _stateManager = stateManager;
  }

  String? get currentToken => _currentToken;

  Future<String?> getValidToken() async {
    try {
      if (_connectionModule == null) {
        _log.error("❌ ConnectionsApiModule not available");
        _updateTokenState(false);
        return null;
      }
      
      // Get token from secure storage
      String? token = await _connectionModule!.getAccessToken();
      if (token == null) {
        _log.error("❌ No access token found in secure storage");
        _updateTokenState(false);
        return null;
      }

      // Check if token is expired
      if (_isTokenExpired(token)) {
        _log.info("🔄 Access token expired, refreshing...");
        // Try to refresh token
        token = await _refreshToken();
        if (token == null) {
          _log.error("❌ Failed to refresh token");
          _updateTokenState(false);
          return null;
        }
      }

      _currentToken = token;
      _updateTokenState(true);
      return token;
    } catch (e) {
      _log.error("❌ Error getting valid token: $e");
      _updateTokenState(false);
      return null;
    }
  }

  void _updateTokenState(bool isValid) {
    if (_stateManager != null) {
      _stateManager!.updatePluginState("websocket", <String, dynamic>{
        "hasValidToken": isValid
      });
    }
  }

  bool _isTokenExpired(String token) {
    try {
      // Decode token without verification
      final parts = token.split('.');
      if (parts.length != 3) return true;

      final payload = json.decode(utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))));
      final exp = payload['exp'] as int?;
      
      if (exp == null) return true;
      
      // Add 5 minutes buffer for token refresh
      return DateTime.now().millisecondsSinceEpoch >= (exp * 1000) - 300000;
    } catch (e) {
      _log.error("❌ Error checking token expiration: $e");
      return true;
    }
  }

  Future<String?> _refreshToken() async {
    try {
      // Get refresh token from secure storage
      String? refreshToken = await _connectionModule!.getRefreshToken();
      if (refreshToken == null) {
        _log.error("❌ No refresh token available");
        _updateTokenState(false);
        return null;
      }

      // Try to refresh the token
      final response = await _connectionModule!.refreshAccessToken(refreshToken);
      
      // If response is null, it means there was an error in the API call
      if (response == null) {
        _log.error("❌ Failed to refresh token");
        await _connectionModule!.clearAuthTokens();
        _updateTokenState(false);
        return null;
      }

      // If response is a string, it's the new token
      if (response is String) {
        _updateTokenState(true);
        return response;
      }

      // If we get here, something unexpected happened
      _log.error("❌ Unexpected response format from token refresh");
      await _connectionModule!.clearAuthTokens();
      _updateTokenState(false);
      return null;
    } catch (e) {
      _log.error("❌ Error refreshing token: $e");
      await _connectionModule!.clearAuthTokens();
      _updateTokenState(false);
      return null;
    }
  }

  void startTokenRefreshTimer() {
    _stopTokenRefreshTimer();
    _tokenRefreshTimer = Timer.periodic(const Duration(minutes: 4), (timer) async {
      _log.info("🔄 Refreshing token...");
      final newToken = await getValidToken();
      if (newToken == null) {
        _log.error("❌ Token refresh failed, stopping timer");
        _stopTokenRefreshTimer();
      }
    });
  }

  void _stopTokenRefreshTimer() {
    _tokenRefreshTimer?.cancel();
    _tokenRefreshTimer = null;
  }

  void dispose() {
    _stopTokenRefreshTimer();
    _currentToken = null;
    _updateTokenState(false);
  }
} 