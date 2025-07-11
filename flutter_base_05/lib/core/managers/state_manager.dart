import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../../tools/logging/logger.dart';

class PluginState {
  final Map<String, dynamic> state;

  PluginState({required this.state});

  /// Ensures all keys are Strings and values are valid JSON types
  factory PluginState.fromDynamic(Map<dynamic, dynamic> rawState) {
    return PluginState(
      state: rawState.map((key, value) => MapEntry(key.toString(), value)),
    );
  }

  /// Merges the new state with the existing one
  PluginState merge(Map<String, dynamic> newState) {
    return PluginState(state: {...state, ...newState});
  }
}

class StateManager with ChangeNotifier {
  static final Logger _log = Logger(); // ✅ Use a static logger for static methods
  static StateManager? _instance;

  final Map<String, PluginState> _pluginStates = {}; // Stores structured plugin states
  Map<String, dynamic> _mainAppState = {'main_state': 'idle'}; // Default main app state


  StateManager._internal() {
    _log.info('StateManager instance created.');
  }

  /// Factory method to provide the singleton instance
  factory StateManager() {
    _instance ??= StateManager._internal();
    return _instance!;
  }

  // ------ Plugin State Methods ------

  bool isPluginStateRegistered(String pluginKey) {
    return _pluginStates.containsKey(pluginKey);
  }

  /// ✅ Strictly register plugin states with `PluginState` structure
  void registerPluginState(String pluginKey, Map<String, dynamic> initialState) {
    if (!_pluginStates.containsKey(pluginKey)) {
      _pluginStates[pluginKey] = PluginState(state: initialState);
      _log.info("✅ Registered plugin state for key: $pluginKey");
      _log.info("📊 Current app state after registration:");
      _logAppState();
      // Use Future.microtask to avoid calling notifyListeners during build
      Future.microtask(() => notifyListeners());
    } else {
      _log.error("⚠️ Plugin state for '$pluginKey' is already registered.");
    }
  }

  /// ✅ Unregister plugin state
  void unregisterPluginState(String pluginKey) {
    if (_pluginStates.containsKey(pluginKey)) {
      _pluginStates.remove(pluginKey);
      _log.info("🗑 Unregistered state for key: $pluginKey");
      _log.info("📊 Current app state after unregistration:");
      _logAppState();
      // Use Future.microtask to avoid calling notifyListeners during build
      Future.microtask(() => notifyListeners());
    } else {
      _log.error("⚠️ Plugin state for '$pluginKey' does not exist.");
    }
  }

  T? getPluginState<T>(String pluginKey) {
    final PluginState? storedState = _pluginStates[pluginKey];

    if (storedState == null) {
      return null; // Ensure we don't attempt to access a null object
    }

    if (T == Map<String, dynamic>) {
      // Ensure that all keys are Strings and cast properly
      return storedState.state.map((key, value) => MapEntry(key.toString(), value)) as T;
    }

    if (storedState.state is T) {
      return storedState.state as T;
    }

    _log.error("❌ Type mismatch: Requested '$T' but found '${storedState.state.runtimeType}' for plugin '$pluginKey'");
    return null;
  }

  /// Log the entire app state for debugging
  void _logAppState() {
    final allStates = getAllStates();
    _log.info("📊 Complete App State:");
    _log.info("🔧 Plugin States: ${allStates['plugin_states']}");
    _log.info("📱 Main App State: ${allStates['main_app_state']}");
    _log.info("📈 Total Plugin States: ${getPluginStateCount()}");
    _log.info("🔑 Registered Keys: ${getRegisteredPluginKeys()}");
  }

  void updatePluginState(String pluginKey, Map<String, dynamic> newState, {bool force = false}) {
    if (!_pluginStates.containsKey(pluginKey)) {
      _log.error("❌ Cannot update state for '$pluginKey' - it is not registered.");
      return;
    }

    final existingState = _pluginStates[pluginKey];

    if (existingState != null) {
      // ✅ Ensure `merge` exists (assuming it's a custom method)
      final newMergedState = existingState.merge(newState);
      _pluginStates[pluginKey] = newMergedState;
      _log.info("✅ Updated state for plugin '$pluginKey'");
      _log.info("📊 Current app state after update:");
      _logAppState();
      // Use Future.microtask to avoid calling notifyListeners during build
      Future.microtask(() => notifyListeners());
    } else {
      _log.error("❌ Cannot update state for '$pluginKey' - existing state is null");
    }
  }

  /// Returns a map of all registered plugin states
  Map<String, Map<String, dynamic>> getAllPluginStates() {
    return _pluginStates.map((key, value) => MapEntry(key, value.state));
  }

  /// Returns a map of all registered states including main app state
  Map<String, dynamic> getAllStates() {
    return {
      'plugin_states': getAllPluginStates(),
      'main_app_state': _mainAppState,
    };
  }

  /// Returns a list of all registered plugin keys
  List<String> getRegisteredPluginKeys() {
    return _pluginStates.keys.toList();
  }

  /// Returns the number of registered plugin states
  int getPluginStateCount() {
    return _pluginStates.length;
  }

  /// Returns true if any plugin state is registered
  bool hasPluginStates() {
    return _pluginStates.isNotEmpty;
  }

  // ------ Main App State Methods ------

  void setMainAppState(Map<String, dynamic> initialState) {
    _mainAppState = {'main_state': 'idle', ...initialState};
    _log.info("📌 Main app state initialized: $_mainAppState");
    _log.info("📊 Current app state after main app state initialization:");
    _logAppState();
    // Use Future.microtask to avoid calling notifyListeners during build
    Future.microtask(() => notifyListeners());
  }

  Map<String, dynamic> get mainAppState => _mainAppState;

  void updateMainAppState(String key, dynamic value) {
    _mainAppState[key] = value;
    _log.info("📌 Main app state updated: key=$key, value=$value");
    _log.info("📊 Current app state after main app state update:");
    _logAppState();
    // Use Future.microtask to avoid calling notifyListeners during build
    Future.microtask(() => notifyListeners());
  }

  T? getMainAppState<T>(String key) {
    return _mainAppState[key] as T?;
  }
}
