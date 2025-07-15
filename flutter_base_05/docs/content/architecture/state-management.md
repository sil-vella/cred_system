# State Management

How state is managed in the Flutter application.

## State Management Pattern

The application uses a combination of:

- **Provider** - For state management
- **StateManager** - For centralized state management
- **ModuleManager** - For module state management
- **ServicesManager** - For service state management

## State Flow

1. **UI Event** → Widget
2. **State Update** → StateManager
3. **Module Update** → ModuleManager
4. **Service Call** → ServicesManager
5. **UI Update** → Widget

