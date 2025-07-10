# Configuration Constants Documentation

## Overview
The `Config` class provides centralized configuration constants for the application, including environment-specific URLs, logging settings, and advertisement IDs. It uses environment variables with default values for flexible deployment configurations.

## Key Features
- Environment-based configuration
- API endpoint management
- WebSocket URL configuration
- Advertisement ID management
- Logging control

## Class Structure

### Config
A static configuration class containing application constants.

#### Properties
- `loggerOn`: Logging control flag
- `appTitle`: Application title
- `apiUrl`: API endpoint URL
- `wsUrl`: WebSocket server URL
- `admobsTopBanner`: Top banner ad ID
- `admobsBottomBanner`: Bottom banner ad ID
- `admobsInterstitial01`: Interstitial ad ID
- `admobsRewarded01`: Rewarded ad ID

## Configuration Values

### Application Settings
```dart
static const bool loggerOn = true;
static const String appTitle = "recall";
```

### API Configuration
```dart
static const String apiUrl = String.fromEnvironment(
  'API_URL_LOCAL',
  defaultValue: 'http://localhost:5000',
);
```

### WebSocket Configuration
```dart
static const String wsUrl = String.fromEnvironment(
  'WS_URL_LOCAL',
  defaultValue: 'ws://195.158.74.150:5000/',
);
```

### Advertisement IDs
```dart
static const String admobsTopBanner = String.fromEnvironment(
  'ADMOBS_TOP_BANNER01',
  defaultValue: '',
);
```

## Environment Variables
- `API_URL_LOCAL`: API endpoint URL
- `WS_URL_LOCAL`: WebSocket server URL
- `ADMOBS_TOP_BANNER01`: Top banner ad ID
- `ADMOBS_BOTTOM_BANNER01`: Bottom banner ad ID
- `ADMOBS_INTERSTITIAL01`: Interstitial ad ID
- `ADMOBS_REWARDED01`: Rewarded ad ID

## Best Practices
1. Use environment variables
2. Provide default values
3. Secure sensitive data
4. Document changes
5. Version control

## Security Considerations
- API endpoint security
- WebSocket connection security
- Advertisement ID protection
- Environment variable handling
- Default value safety

## Integration Points
The configuration integrates with:
- Logger system
- API services
- WebSocket services
- Advertisement system
- Environment setup

## Usage Examples

### Accessing Configuration
```dart
// Using API URL
final apiEndpoint = Config.apiUrl;

// Using WebSocket URL
final wsEndpoint = Config.wsUrl;

// Checking logger status
if (Config.loggerOn) {
  // Perform logging
}
```

## Deployment Considerations
- Environment setup
- Default values
- Security measures
- Configuration verification
- Version management 