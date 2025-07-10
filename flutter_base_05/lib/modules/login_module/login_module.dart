import 'package:flutter/material.dart';
import '../connections_api_module/connections_api_module.dart';
import 'package:provider/provider.dart';
import '../../core/00_base/module_base.dart';
import '../../core/managers/module_manager.dart';
import '../../core/managers/services_manager.dart';
import '../../core/services/shared_preferences.dart';
import '../../tools/logging/logger.dart';
import '../../core/managers/state_manager.dart';

class LoginModule extends ModuleBase {
  static final Logger _log = Logger();

  late ServicesManager _servicesManager;
  late ModuleManager _localModuleManager;
  SharedPrefManager? _sharedPref;
  ConnectionsApiModule? _connectionModule;
  BuildContext? _currentContext;

  /// ✅ Constructor with module key and dependencies
  LoginModule() : super("login_module", dependencies: ["connections_api_module"]);

  @override
  void initialize(BuildContext context, ModuleManager moduleManager) {
    super.initialize(context, moduleManager);
    _localModuleManager = moduleManager;
    _initDependencies(context);
    _log.info('✅ LoginModule initialized with context.');
  }

  /// ✅ Fetch dependencies once per context
  void _initDependencies(BuildContext context) {
    _servicesManager = Provider.of<ServicesManager>(context, listen: false);
    _sharedPref = _servicesManager.getService<SharedPrefManager>('shared_pref');
    _connectionModule = _localModuleManager.getModuleByType<ConnectionsApiModule>();
    _currentContext = context;

    // Initialize login state in StateManager after the current frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final stateManager = Provider.of<StateManager>(context, listen: false);
      stateManager.registerPluginState("login", {
        "isLoggedIn": _sharedPref?.getBool('is_logged_in') ?? false,
        "userId": _sharedPref?.getInt('user_id'),
        "username": _sharedPref?.getString('username'),
        "email": _sharedPref?.getString('email'),
        "error": null
      });
    });
  }

  Future<Map<String, dynamic>> getUserStatus(BuildContext context) async {
    _initDependencies(context);

    if (_sharedPref == null) {
      _log.error("❌ SharedPrefManager not available.");
      return {"error": "Service not available."};
    }

    bool isLoggedIn = _sharedPref!.getBool('is_logged_in') ?? false;

    if (!isLoggedIn) {
      return {"status": "logged_out"};
    }

    return {
      "status": "logged_in",
      "user_id": _sharedPref!.getInt('user_id'),
      "username": _sharedPref!.getString('username'),
      "email": _sharedPref!.getString('email'),
    };
  }

  Future<Map<String, dynamic>> registerUser({
    required BuildContext context,
    required String username,
    required String email,
    required String password,
  }) async {
    _initDependencies(context);

    if (_connectionModule == null) {
      _log.error("❌ Connection module not available.");
      return {"error": "Service not available."};
    }

    // Validate username
    if (username.length < 3) {
      return {"error": "Username must be at least 3 characters long"};
    }
    if (username.length > 20) {
      return {"error": "Username cannot be longer than 20 characters"};
    }
    if (!RegExp(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$').hasMatch(username)) {
      return {"error": "Username can only contain letters, numbers, underscores, and hyphens"};
    }
    if (RegExp(r'[-_]{2,}').hasMatch(username)) {
      return {"error": "Username cannot contain consecutive special characters"};
    }
    if (username.startsWith('_') || username.startsWith('-') || 
        username.endsWith('_') || username.endsWith('-')) {
      return {"error": "Username cannot start or end with special characters"};
    }

    // Validate email format
    final emailRegex = RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');
    if (!emailRegex.hasMatch(email)) {
      return {"error": "Invalid email format. Please enter a valid email address."};
    }

    // Validate password requirements
    if (password.length < 6) {
      return {"error": "Password must be at least 6 characters long"};
    }

    if (!RegExp(r'[0-9]').hasMatch(password)) {
      return {"error": "Password must contain at least 1 number"};
    }

    if (!RegExp(r'[!@#$%^&*(),.?":{}|<>]').hasMatch(password)) {
      return {"error": "Password must contain at least 1 special character"};
    }

    try {
      _log.info("⚡ Sending registration request...");
      _log.info("📤 Registration data: username=$username, email=$email");
      
      final response = await _connectionModule!.sendPostRequest(
        "/register",
        {
          "username": username,
          "email": email,
          "password": password,
        },
      );

      _log.info("📥 Registration response: $response");

      if (response is Map) {
        if (response["message"] == "User registered successfully") {
          _log.info("✅ User registered successfully.");
          return {"success": "Registration successful. Please log in."};
        } else if (response["error"] != null) {
          _log.error("❌ Registration failed: ${response["error"]}");
          
          // Handle rate limiting errors
          if (response["status"] == 429) {
            return {
              "error": response["error"] ?? "Too many registration attempts. Please try again later.",
              "isRateLimited": true
            };
          }
          
          return {"error": response["error"]};
        }
      }

      _log.error("❌ Unexpected response format: $response");
      return {"error": "Unexpected server response format"};
    } catch (e) {
      _log.error("❌ Registration error: $e");
      return {"error": "Server error. Check network connection."};
    }
  }

  Future<Map<String, dynamic>> loginUser({
    required BuildContext context,
    required String email,
    required String password,
  }) async {
    _initDependencies(context);
    _log.info("🔑 Starting login process for email: $email");

    if (_connectionModule == null || _sharedPref == null) {
      _log.error("❌ Missing required modules for login.");
      return {"error": "Service not available."};
    }

    try {
      _log.info("⚡ Preparing login request...");
      _log.info("📤 Sending login request to backend...");
      final response = await _connectionModule!.sendPostRequest(
        "/login",
        {"email": email, "password": password},
      );
      _log.info("📥 Received login response: $response");

      // Handle error responses
      if (response?["status"] == 409 || response?["code"] == "CONFLICT") {
        _log.info("⚠️ Login failed: Conflict detected");
        return {
          "error": response["message"] ?? "A conflict occurred",
          "user": response["user"]
        };
      }

      if (response?["error"] != null || response?["message"]?.contains("error") == true) {
        String errorMessage = response?["message"] ?? response?["error"] ?? "Unknown error occurred";
        _log.error("❌ Login failed: $errorMessage");
        
        // Handle rate limiting errors
        if (response?["status"] == 429) {
          return {
            "error": errorMessage,
            "isRateLimited": true
          };
        }
        
        return {"error": errorMessage};
      }

      // Handle successful login
      if (response?["message"] == "Login successful" || response?["success"] == true) {
        _log.info("✅ Login successful");
        
        // Store user data in SharedPreferences
        await _sharedPref!.setBool('is_logged_in', true);
        await _sharedPref!.setInt('user_id', response?["user_id"] ?? 0);
        await _sharedPref!.setString('username', response?["username"] ?? "");
        await _sharedPref!.setString('email', email);
        
        // Update state manager
        final stateManager = Provider.of<StateManager>(context, listen: false);
        stateManager.updatePluginState("login", {
          "isLoggedIn": true,
          "userId": response?["user_id"],
          "username": response?["username"],
          "email": email,
          "error": null
        });
        
        return {
          "success": "Login successful",
          "user_id": response?["user_id"],
          "username": response?["username"],
          "email": email
        };
      }

      _log.error("❌ Unexpected login response: $response");
      return {"error": "Unexpected server response"};
    } catch (e) {
      _log.error("❌ Login error: $e");
      return {"error": "Server error. Check network connection."};
    }
  }

  Future<Map<String, dynamic>> logoutUser(BuildContext context) async {
    _initDependencies(context);
    _log.info("🔓 Starting logout process");

    try {
      // Clear stored user data
      await _sharedPref!.setBool('is_logged_in', false);
      await _sharedPref!.remove('user_id');
      await _sharedPref!.remove('username');
      await _sharedPref!.remove('email');
      
      // Update state manager
      final stateManager = Provider.of<StateManager>(context, listen: false);
      stateManager.updatePluginState("login", {
        "isLoggedIn": false,
        "userId": null,
        "username": null,
        "email": null,
        "error": null
      });
      
      _log.info("✅ Logout successful");
      return {"success": "Logout successful"};
    } catch (e) {
      _log.error("❌ Logout error: $e");
      return {"error": "Logout failed"};
    }
  }
}
