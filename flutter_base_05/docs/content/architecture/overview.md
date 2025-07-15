# System Overview

High-level architecture of the Credit System Flutter frontend.

## Codebase Statistics

- **Total Files:** 35
- **Total Classes:** 26
- **Total Widgets:** 20
- **Total Managers:** 14
- **Total Services:** 2
- **Total Functions:** 130
- **Total Enums:** 1

## Module Structure

- `lib.main`
- `lib.stream_socket`
- `lib.tools.logging.logger`
- `lib.core.00_base.screen_base`
- `lib.core.00_base.module_base`
- `lib.core.00_base.service_base`
- `lib.core.00_base.drawer_base`
- `lib.core.managers.app_manager`
- `lib.core.managers.event_bus`
- `lib.core.managers.state_manager`
- `lib.core.managers.navigation_manager`
- `lib.core.managers.module_registry`
- `lib.core.managers.hooks_manager`
- `lib.core.managers.auth_manager`
- `lib.core.managers.module_manager`
- `lib.core.managers.services_manager`
- `lib.core.services.shared_preferences`
- `lib.core.services.ticker_timer.ticker_timer`
- `lib.core.services.ticker_timer.ticker_timer_component`
- `lib.utils.consts.theme_consts`
- `lib.utils.consts.config`
- `lib.models.credit_bucket`
- `lib.screens.room_management_screen`
- `lib.screens.account_screen.account_screen`
- `lib.modules.modules_template`
- `lib.modules.audio_module.audio_module`
- `lib.modules.main_helper_module.main_helper_module`
- `lib.modules.home_module.home_screen`
- `lib.modules.admobs.interstitial.interstitial_ad`
- `lib.modules.admobs.rewarded.rewarded_ad`
- `lib.modules.admobs.banner.banner_ad`
- `lib.modules.login_module.login_module`
- `lib.modules.animations_module.animations_module`
- `lib.modules.connections_api_module.interceptor`
- `lib.modules.connections_api_module.connections_api_module`

## Architecture Layers

1. **UI Layer** - Flutter widgets and screens
2. **State Layer** - State management and data flow
3. **Service Layer** - External service interactions
4. **Manager Layer** - Core application managers
5. **Utils Layer** - Common utilities and tools
