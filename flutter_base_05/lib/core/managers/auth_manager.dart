import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../tools/logging/logger.dart';
import '../services/shared_preferences.dart';
import '../managers/services_manager.dart';
import '../managers/state_manager.dart';
import '../managers/module_manager.dart';
import '../../modules/connections_api_module/connections_api_module.dart';

enum AuthStatus {
  loggedIn,
  loggedOut,
  tokenExpired,
  sessionExpired,
  error
}

class AuthManager extends ChangeNotifier {
  static final Logger _log = Logger();
  static final AuthManager _instance = AuthManager._internal();
  
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  SharedPrefManager? _sharedPref;
  ConnectionsApiModule? _connectionModule;
  
  AuthStatus _currentStatus = AuthStatus.loggedOut;
  AuthStatus get currentStatus => _currentStatus;
  
  bool _isValidating = false;
  bool get isValidating => _isValidating;

  factory AuthManager() => _instance;
  AuthManager._internal();

  /// ✅ Initialize AuthManager with dependencies
  void initialize(BuildContext context) {
    final servicesManager = Provider.of<ServicesManager>(context, listen: false);
    _sharedPref = servicesManager.getService<SharedPrefManager>('shared_pref');
    
    final moduleManager = Provider.of<ModuleManager>(context, listen: false);
    _connectionModule = moduleManager.getModuleByType<ConnectionsApiModule>();
    
    _log.info('✅ AuthManager initialized');
  }

  /// ✅ Validate session on app startup
  Future<AuthStatus> validateSessionOnStartup() async {
    if (_sharedPref == null) {
      _log.error('❌ SharedPrefManager not available');
      return AuthStatus.error;
    }

    _isValidating = true;
    notifyListeners();

    try {
      _log.info('🔍 Validating session on startup...');

      // Step 1: Check if user thinks they're logged in
      final isLoggedIn = _sharedPref!.getBool('is_logged_in') ?? false;
      if (!isLoggedIn) {
        _log.info('ℹ️ User not logged in');
        _currentStatus = AuthStatus.loggedOut;
        _isValidating = false;
        notifyListeners();
        return AuthStatus.loggedOut;
      }

      // Step 2: Check if JWT token exists
      final accessToken = await _secureStorage.read(key: 'access_token');
      if (accessToken == null) {
        _log.info('⚠️ No access token found, clearing stored data');
        await _clearStoredData();
        _currentStatus = AuthStatus.tokenExpired;
        _isValidating = false;
        notifyListeners();
        return AuthStatus.tokenExpired;
      }

      // Step 3: Validate token with backend (optional but recommended)
      final isValid = await _validateTokenWithBackend(accessToken);
      if (!isValid) {
        _log.info('⚠️ Token validation failed, attempting refresh');
        
        // Try to refresh token
        final refreshToken = await _secureStorage.read(key: 'refresh_token');
        if (refreshToken != null && _connectionModule != null) {
          final newToken = await _connectionModule!.refreshAccessToken(refreshToken);
          if (newToken != null) {
            _log.info('✅ Token refreshed successfully');
            _currentStatus = AuthStatus.loggedIn;
            _isValidating = false;
            notifyListeners();
            return AuthStatus.loggedIn;
          }
        }
        
        _log.info('⚠️ Token refresh failed, clearing stored data');
        await _clearStoredData();
        _currentStatus = AuthStatus.tokenExpired;
        _isValidating = false;
        notifyListeners();
        return AuthStatus.tokenExpired;
      }

      // Step 4: Check session age (optional)
      final lastLogin = _sharedPref!.getString('last_login_timestamp');
      if (lastLogin != null) {
        final lastLoginTime = DateTime.parse(lastLogin);
        final daysSinceLogin = DateTime.now().difference(lastLoginTime).inDays;
        if (daysSinceLogin > 30) { // Configurable
          _log.info('⚠️ Session expired (${daysSinceLogin} days old)');
          await _clearStoredData();
          _currentStatus = AuthStatus.sessionExpired;
          _isValidating = false;
          notifyListeners();
          return AuthStatus.sessionExpired;
        }
      }

      _log.info('✅ Session validation successful');
      _currentStatus = AuthStatus.loggedIn;
      _isValidating = false;
      notifyListeners();
      return AuthStatus.loggedIn;

    } catch (e) {
      _log.error('❌ Session validation error: $e');
      await _clearStoredData();
      _currentStatus = AuthStatus.error;
      _isValidating = false;
      notifyListeners();
      return AuthStatus.error;
    }
  }

  /// ✅ Validate token with backend
  Future<bool> _validateTokenWithBackend(String token) async {
    if (_connectionModule == null) {
      _log.info('⚠️ Connection module not available, skipping backend validation');
      return true; // Assume valid if we can't validate
    }

    try {
      // You can implement a lightweight token validation endpoint
      // For now, we'll assume the token is valid if it exists
      // In production, you might want to call /auth/validate or similar
      return true;
    } catch (e) {
      _log.error('❌ Token validation error: $e');
      return false;
    }
  }

  /// ✅ Handle authentication state changes
  Future<void> handleAuthState(BuildContext context, AuthStatus status) async {
    final stateManager = Provider.of<StateManager>(context, listen: false);
    
    switch (status) {
      case AuthStatus.loggedIn:
        // User is logged in, load their data
        final userData = {
          "isLoggedIn": true,
          "userId": _sharedPref?.getString('user_id'),
          "username": _sharedPref?.getString('username'),
          "email": _sharedPref?.getString('email'),
        };
        
        stateManager.updateModuleState("login", userData);
        _log.info('✅ User logged in: ${userData['username']}');
        break;
        
      case AuthStatus.loggedOut:
      case AuthStatus.tokenExpired:
      case AuthStatus.sessionExpired:
        // User needs to log in
        stateManager.updateModuleState("login", {
          "isLoggedIn": false,
          "userId": null,
          "username": null,
          "email": null,
        });
        
        String message = "Please log in";
        if (status == AuthStatus.tokenExpired) {
          message = "Session expired. Please log in again.";
        } else if (status == AuthStatus.sessionExpired) {
          message = "Session expired due to inactivity. Please log in again.";
        }
        
        _log.info('ℹ️ User needs to log in: $message');
        break;
        
      case AuthStatus.error:
        // Handle error state
        stateManager.updateModuleState("login", {
          "isLoggedIn": false,
          "userId": null,
          "username": null,
          "email": null,
          "error": "Authentication error occurred"
        });
        _log.error('❌ Authentication error occurred');
        break;
    }
  }

  /// ✅ Clear all stored authentication data
  Future<void> _clearStoredData() async {
    try {
      // Clear secure storage
      await _secureStorage.delete(key: 'access_token');
      await _secureStorage.delete(key: 'refresh_token');
      
      // Clear shared preferences
      if (_sharedPref != null) {
        await _sharedPref!.setBool('is_logged_in', false);
        await _sharedPref!.remove('user_id');
        await _sharedPref!.remove('username');
        await _sharedPref!.remove('email');
        await _sharedPref!.remove('last_login_timestamp');
      }
      
      _log.info('🗑️ Cleared all stored authentication data');
    } catch (e) {
      _log.error('❌ Error clearing stored data: $e');
    }
  }

  /// ✅ Get current user data
  Map<String, dynamic> getCurrentUserData() {
    if (_sharedPref == null) return {};
    
    return {
      "isLoggedIn": _sharedPref!.getBool('is_logged_in') ?? false,
      "userId": _sharedPref!.getString('user_id'),
      "username": _sharedPref!.getString('username'),
      "email": _sharedPref!.getString('email'),
    };
  }

  /// ✅ Check if user is currently logged in
  bool get isLoggedIn {
    return _sharedPref?.getBool('is_logged_in') ?? false;
  }

  /// ✅ Get current JWT token
  Future<String?> getCurrentToken() async {
    return await _secureStorage.read(key: 'access_token');
  }

  @override
  void dispose() {
    super.dispose();
    _log.info('🛑 AuthManager disposed');
  }
} 