import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http_interceptor/http_interceptor.dart';
import 'package:http/http.dart';

class AuthInterceptor implements InterceptorContract {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  /// ✅ Decide if the request should be intercepted
  @override
  bool shouldInterceptRequest() => true;

  /// ✅ Decide if the response should be intercepted
  @override
  bool shouldInterceptResponse() => true;

  /// ✅ Modify the request to add an authorization token
  @override
  Future<BaseRequest> interceptRequest({required BaseRequest request}) async {
    String? token = await _storage.read(key: 'auth_token');
    if (token != null) {
      request.headers["Authorization"] = "Bearer $token"; // ✅ Auto-add token
    }
    return request;
  }

  /// ✅ Modify the response if needed (e.g., refresh token on 401)
  @override
  Future<BaseResponse> interceptResponse({required BaseResponse response}) async {
    if (response is Response && response.statusCode == 401) {
      // ✅ Handle Unauthorized (maybe clear token or refresh it)
      await _storage.delete(key: 'auth_token');
    }
    return response;
  }
}
