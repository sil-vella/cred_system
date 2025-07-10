import '../../../../../../tools/logging/logger.dart';

class WebSocketResult {
  final String eventType;
  final dynamic data;
  final String? error;
  final bool isSuccess;

  WebSocketResult({
    required this.eventType,
    this.data,
    this.error,
    required this.isSuccess,
  });

  factory WebSocketResult.success(String eventType, {dynamic data}) {
    return WebSocketResult(
      eventType: eventType,
      data: data,
      isSuccess: true,
    );
  }

  factory WebSocketResult.error(String eventType, String error) {
    return WebSocketResult(
      eventType: eventType,
      error: error,
      isSuccess: false,
    );
  }
}

class ResultHandler {
  static final Logger _log = Logger();

  WebSocketResult createSuccessResult(String eventType, {dynamic data}) {
    _log.info("✅ $eventType successful: $data");
    return WebSocketResult.success(eventType, data: data);
  }

  WebSocketResult createErrorResult(String eventType, String error) {
    _log.error("❌ $eventType failed: $error");
    return WebSocketResult.error(eventType, error);
  }

  WebSocketResult createUnknownErrorResult(String eventType, String error) {
    _log.error("❌ Unknown error in $eventType: $error");
    return WebSocketResult.error(eventType, "An unknown error occurred: $error");
  }

  WebSocketResult createNoConnectionResult() {
    return WebSocketResult.error('connection', 'No WebSocket connection available');
  }

  WebSocketResult createInvalidTokenResult() {
    return WebSocketResult.error('connection', 'Invalid or expired token');
  }

  WebSocketResult createRateLimitResult() {
    return WebSocketResult.error('connection', 'Rate limit exceeded');
  }
} 