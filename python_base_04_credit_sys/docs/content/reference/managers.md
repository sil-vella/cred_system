# Managers

Core managers that handle different aspects of the application.

## StateManager

**File:** `python_base_04_credit_sys/core/managers/state_manager.py`

**Type:** class

**Methods:**
- `__new__()`
- `__init__()`
- `get_instance()`
- `reset_instance()`
- `register_state()`
- `get_state()`
- `update_state()`
- `delete_state()`
- `get_state_history()`
- `register_callback()`
- `get_states_by_type()`
- `get_active_states()`
- `_validate_transition()`
- `_update_transition_rules()`
- `_add_to_history()`
- `_trigger_state_callbacks()`
- `_store_state_in_redis()`
- `_get_state_from_redis()`
- `_remove_state_from_redis()`
- `_store_state_in_database()`
- `_get_state_from_database()`
- `_mark_state_deleted_in_database()`
- `health_check()`

**Attributes:**
- `_instance`
- `_initialized`
- `allowed_transitions`
- `history_entry`
- `state_record`
- `redis_state`
- `db_state`
- `current_state`
- `updated_state`
- `transition_type`
- `history`
- `states`
- `active_states`
- `total_states`
- `history`

::: core.managers.state_manager.StateManager
    handler: python
    options:
      show_source: true
      show_root_heading: true

## core.managers.state_manager

**File:** `python_base_04_credit_sys/core/managers/state_manager.py`

**Type:** module

## core.managers.__init__

**File:** `python_base_04_credit_sys/core/managers/__init__.py`

**Type:** module

## VaultManager

**File:** `python_base_04_credit_sys/core/managers/vault_manager.py`

**Type:** class

**Methods:**
- `__init__()`
- `_validate_config()`
- `_authenticate()`
- `_ensure_authenticated()`
- `get_secret()`
- `get_secret_value()`
- `get_mongodb_secrets()`
- `get_redis_secrets()`
- `get_app_secrets()`
- `get_stripe_secrets()`
- `get_monitoring_secrets()`
- `health_check()`
- `get_connection_info()`

**Attributes:**
- `missing_vars`
- `success`
- `secret`
- `auth_data`
- `response`
- `headers`
- `api_path`
- `response`
- `response`
- `auth_result`
- `auth_info`
- `secret_data`
- `health_data`
- `secrets`

::: core.managers.vault_manager.VaultManager
    handler: python
    options:
      show_source: true
      show_root_heading: true

## core.managers.vault_manager

**File:** `python_base_04_credit_sys/core/managers/vault_manager.py`

**Type:** module

## core.managers.secret_manager

**File:** `python_base_04_credit_sys/core/managers/secret_manager.py`

**Type:** module

## EncryptionManager

**File:** `python_base_04_credit_sys/core/managers/encryption_manager.py`

**Type:** class

**Methods:**
- `__init__()`
- `_initialize_fernet()`
- `encrypt_data()`
- `decrypt_data()`
- `encrypt_sensitive_fields()`
- `decrypt_sensitive_fields()`

**Attributes:**
- `SALT_LENGTH`
- `ITERATIONS`
- `key`
- `kdf`
- `derived_key`
- `encrypted_data`
- `encrypted_data`
- `decrypted_data`
- `data`
- `decrypted_data`

::: core.managers.encryption_manager.EncryptionManager
    handler: python
    options:
      show_source: true
      show_root_heading: true

## core.managers.encryption_manager

**File:** `python_base_04_credit_sys/core/managers/encryption_manager.py`

**Type:** module

