import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart' as launcher;
import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http_interceptor/http_interceptor.dart';

import '../../core/00_base/module_base.dart';
import '../../core/managers/module_manager.dart';
import '../../tools/logging/logger.dart';
import 'interceptor.dart';

class ConnectionsApiModule extends ModuleBase {
  static final Logger _log = Logger();
  final String baseUrl;
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();

  /// ✅ Use InterceptedClient instead of normal `http`
  final InterceptedClient client = InterceptedClient.build(
    interceptors: [AuthInterceptor()],
    requestTimeout: const Duration(seconds: 10),
  );

  /// ✅ Constructor with module key and dependencies
  ConnectionsApiModule(this.baseUrl) : super('connections_api_module', dependencies: []);

  @override
  void initialize(BuildContext context, ModuleManager moduleManager) {
    super.initialize(context, moduleManager);
    _log.info('✅ ConnectionsApiModule initialized with context.');
    _sendTestRequest();
  }

  /// Generate both HTTP and app deep links for a given path
  static Map<String, String> generateLinks(String path) {
    return {
      'http': 'https://example.com\$path',
      'app': 'recall://\$path'
    };
  }

  /// Launch a URL, either in browser or app
  static Future<bool> launchUrl(String url) async {
    final uri = Uri.parse(url);
    try {
      return await launcher.launchUrl(
        uri,
        mode: launcher.LaunchMode.externalApplication
      );
    } catch (e) {
      _log.error('❌ Failed to launch URL: $url', error: e);
      return false;
    }
  }

  /// ✅ Update authentication tokens
  Future<void> updateAuthTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    try {
      await _secureStorage.write(key: 'access_token', value: accessToken);
      await _secureStorage.write(key: 'refresh_token', value: refreshToken);
      _log.info('✅ Auth tokens updated successfully');
    } catch (e) {
      _log.error('❌ Failed to update auth tokens: $e');
      rethrow;
    }
  }

  /// ✅ Clear authentication tokens
  Future<void> clearAuthTokens() async {
    try {
      await _secureStorage.delete(key: 'access_token');
      await _secureStorage.delete(key: 'refresh_token');
      _log.info('✅ Auth tokens cleared successfully');
    } catch (e) {
      _log.error('❌ Failed to clear auth tokens: $e');
      rethrow;
    }
  }

  /// ✅ Get current access token
  Future<String?> getAccessToken() async {
    return await _secureStorage.read(key: 'access_token');
  }

  /// ✅ Get current refresh token
  Future<String?> getRefreshToken() async {
    return await _secureStorage.read(key: 'refresh_token');
  }

  /// ✅ Refresh access token using refresh token
  Future<String?> refreshAccessToken(String refreshToken) async {
    try {
      _log.info('🔄 Refreshing access token...');
      
      final response = await sendPostRequest('/auth/refresh', {
        'refresh_token': refreshToken
      });
      
      // Check if response is an error
      if (response is Map && response.containsKey('error')) {
        _log.error('❌ Token refresh error: ${response['error']}');
        return null;
      }
      
      // Check if response has access token
      if (response is Map && response.containsKey('access_token')) {
        await updateAuthTokens(
          accessToken: response['access_token'],
          refreshToken: response['refresh_token'] ?? refreshToken
        );
        _log.info('✅ Token refreshed successfully');
        return response['access_token'];
      }
      
      _log.error('❌ Failed to refresh token: Invalid response format');
      return null;
    } catch (e) {
      _log.error('❌ Failed to refresh token: $e');
      return null;
    }
  }

  /// ✅ GET Request without manually adding tokens
  Future<dynamic> sendGetRequest(String route) async {
    final url = Uri.parse('$baseUrl$route');

    try {
      final response = await client.get(url);
      _log.info('📡 GET Request: $url | Status: ${response.statusCode}');
      return _processResponse(response);
    } catch (e) {
      return _handleError('GET', url, e);
    }
  }

  /// ✅ POST Request without manually adding tokens
  Future<dynamic> sendPostRequest(String route, Map<String, dynamic> data) async {
    final url = Uri.parse('$baseUrl$route');

    try {
      final response = await client.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(data),
      );
      return _processResponse(response);
    } catch (e) {
      return _handleError('POST', url, e);
    }
  }

  /// ✅ Unified Request Method
  Future<dynamic> sendRequest(String route, {required String method, Map<String, dynamic>? data}) async {
    final url = Uri.parse('$baseUrl$route');
    http.Response response;

    try {
      final headers = {'Content-Type': 'application/json'};
      
      switch (method.toUpperCase()) {
        case 'GET':
          response = await client.get(url);
          break;
        case 'POST':
          response = await client.post(url, headers: headers, body: jsonEncode(data ?? {}));
          break;
        case 'PUT':
          response = await client.put(url, headers: headers, body: jsonEncode(data ?? {}));
          break;
        case 'DELETE':
          response = await client.delete(url);
          break;
        default:
          throw Exception('❌ Unsupported HTTP method: $method');
      }

      _log.info('📡 $method Request: $url | Status: ${response.statusCode}');
      return _processResponse(response);
    } catch (e) {
      return _handleError(method, url, e);
    }
  }

  /// ✅ Process Server Response
  dynamic _processResponse(http.Response response) {
    if (response.body.isNotEmpty) {
      if (response.statusCode >= 200 && response.statusCode < 300) {
        _log.debug('📥 Response Body: [Redacted for Security]');
      } else {
        _log.error('📥 Error Response Body: ${response.body}');
      }
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body);
    } else if (response.statusCode == 401) {
      _log.error('⚠️ Unauthorized: Clearing token...');
      const FlutterSecureStorage().delete(key: 'auth_token');
      return {"message": "Session expired. Please log in again.", "error": "Unauthorized"};
    } else {
      _log.error('⚠️ Server Error: ${response.statusCode}');
      try {
        final decodedResponse = jsonDecode(response.body);
        // Ensure we always have a message field for errors
        if (!decodedResponse.containsKey('message') && decodedResponse.containsKey('error')) {
          decodedResponse['message'] = decodedResponse['error'];
        }
        return decodedResponse;
      } catch (e) {
        _log.error('❌ Failed to parse error response: $e');
        return {
          "message": "An unexpected error occurred",
          "error": "Server error",
          "details": response.body
        };
      }
    }
  }

  /// ✅ Handle Errors with Detailed Logging
  Map<String, dynamic> _handleError(String method, Uri url, Object e) {
    _log.error('❌ $method request failed for $url: $e');
    return {
      "message": "Failed to connect to server. Please check your internet connection.",
      "error": "$method request failed",
      "details": e.toString()
    };
  }

  /// ✅ Send test request to verify connection
  void _sendTestRequest() {
    _log.info('🔍 Testing API connection to: $baseUrl');
    sendGetRequest('/health').then((response) {
      _log.info('✅ API connection test successful: $response');
    }).catchError((error) {
      _log.error('❌ API connection test failed: $error');
    });
  }
}