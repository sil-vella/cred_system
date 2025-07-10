import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../tools/logging/logger.dart';
import 'hooks_manager.dart';
import 'module_manager.dart';
import '../00_base/module_base.dart';

class AppManager extends ChangeNotifier {
  static final Logger _log = Logger();
  static final AppManager _instance = AppManager._internal();
  static late BuildContext globalContext;

  bool _isInitialized = false;
  bool get isInitialized => _isInitialized;

  factory AppManager() => _instance;
  AppManager._internal();

  final HooksManager _hooksManager = HooksManager();

  Future<void> _initializeModules(BuildContext context) async {
    _log.info('🚀 Initializing modules...');

    final moduleManager = Provider.of<ModuleManager>(context, listen: false);
    
    // Initialize all registered modules
    await moduleManager.initializeModules(context);

    _isInitialized = true;
    notifyListeners();
    _log.info('✅ All modules initialized successfully.');
  }

  Future<void> initializeApp(BuildContext context) async {
    if (!_isInitialized) {
      Future.delayed(Duration.zero, () {
        if (Navigator.canPop(context)) {
          context.go('/');
        }
      });
      await _initializeModules(context);
      _isInitialized = true;
    }
  }

  /// ✅ Get module status for health checks
  Map<String, dynamic> getModuleStatus(BuildContext context) {
    final moduleManager = Provider.of<ModuleManager>(context, listen: false);
    return moduleManager.getModuleStatus();
  }

  /// ✅ Check if all modules are healthy
  bool checkModuleHealth(BuildContext context) {
    final moduleStatus = getModuleStatus(context);
    final totalModules = moduleStatus['total_modules'] as int;
    final initializedModules = moduleStatus['initialized_modules'] as int;
    final errors = moduleStatus['initialization_errors'] as Map<String, dynamic>;
    
    return totalModules > 0 && initializedModules == totalModules && errors.isEmpty;
  }
}
