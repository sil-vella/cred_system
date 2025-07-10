# Animations Module Documentation

## Overview
The `AnimationsModule` is a utility module that provides a collection of reusable animations for the application. It manages animation controllers and provides various animation effects for UI elements.

## Key Features
- Multiple animation types
- Controller management
- Confetti effects
- Resource cleanup
- Performance optimization
- Animation customization

## Class Structure

### AnimationsModule
Extends `ModuleBase` and manages animations.

#### Properties
- `_controllers`: List of animation controllers
- `_confettiControllers`: Map of confetti controllers
- `_log`: Logger instance

#### Methods
- `dispose`: Cleans up resources
- `registerController`: Registers animation controllers
- `playConfetti`: Triggers confetti animation
- Various animation application methods

## Animation Types

### Basic Animations
- Fade: Opacity transitions
- Scale: Size transformations
- Slide: Position movements
- Bounce: Elastic movements
- Shake and Drop: Combined effects
- Side-to-Side: Horizontal movements

## Usage Examples

### Fade Animation
```dart
final controller = AnimationController(
  vsync: this,
  duration: const Duration(seconds: 1),
);
final animatedWidget = animationsModule.applyFadeAnimation(
  child: widget,
  controller: controller,
);
```

### Scale Animation
```dart
final animatedWidget = animationsModule.applyScaleAnimation(
  child: widget,
  controller: controller,
  begin: 0.8,
  end: 1.2,
);
```

### Confetti Effect
```dart
animationsModule.playConfetti(key: 'celebration');
```

## Animation Lifecycle
1. Controller creation
2. Animation registration
3. Animation execution
4. Resource cleanup
5. Controller disposal

## Resource Management
- Controller tracking
- Memory cleanup
- Performance monitoring
- Resource optimization

## Best Practices
1. Proper controller disposal
2. Efficient animation usage
3. Performance optimization
4. Memory management
5. Error handling

## Error Handling
- Controller validation
- Resource cleanup
- Animation state checks
- Memory leak prevention

## Dependencies
- `flutter/material.dart`
- `confetti` package
- `Logger`

## Integration Points
The AnimationsModule integrates with:
- `ModuleManager`: For module access
- `ServicesManager`: For service access
- `SharedPrefManager`: For preferences

## Performance Considerations
- Controller efficiency
- Animation optimization
- Memory usage
- Resource cleanup
- Frame rate impact

## Animation Customization
- Duration control
- Curve selection
- Effect parameters
- Timing adjustments
- Custom sequences

## Accessibility
- Animation duration control
- Reduced motion support
- Performance optimization
- User preferences
- System settings 