# System Overview

High-level architecture of the Credit System Python backend.

## Codebase Statistics

- **Total Files:** 25
- **Total Classes:** 14
- **Total Functions:** 4
- **Total Modules:** 25

## Module Structure

- `app`
- `tools.logger.audit_logger`
- `tools.error_handling.error_handler`
- `core.metrics`
- `core.managers.state_manager`
- `core.managers.vault_manager`
- `core.managers.secret_manager`
- `core.managers.encryption_manager`
- `core.modules.base_module`
- `utils.exceptions.validation_exceptions`
- `utils.validation.payload_validator`
- `utils.validation.sanitizer`

## Architecture Layers

1. **Managers Layer** - Core application managers
2. **Modules Layer** - Business logic modules
3. **Services Layer** - External service interactions
4. **Utils Layer** - Common utilities and tools
