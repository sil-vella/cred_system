# Audio Module Documentation

## Overview
The `AudioModule` is a comprehensive audio management system that handles sound playback, preloading, and volume control. It provides a robust framework for managing game sounds, music, and effects.

## Key Features
- Sound preloading
- Multiple sound categories
- Volume control
- Mute functionality
- Sound looping
- Resource management
- State persistence

## Class Structure

### AudioModule
Extends `ModuleBase` and manages audio playback.

#### Properties
- `_isMuted`: Global mute state
- `_audioPlayers`: Active audio players
- `_preloadedPlayers`: Preloaded audio players
- `_currentlyPlaying`: Currently playing sounds
- `_random`: Random number generator

#### Sound Categories
- `correctSounds`: Success feedback sounds
- `incorrectSounds`: Error feedback sounds
- `levelUpSounds`: Level progression sounds
- `flushingFiles`: Transition sounds

## Audio Management

### Sound Playback
- Single sound playback
- Random sound selection
- Looping sounds
- Volume control
- Mute control

### Resource Management
- Sound preloading
- Player cleanup
- Memory management
- Resource optimization

## Usage Examples

### Playing a Sound
```dart
await audioModule.playFromList(
  audioModule.correctSounds,
  volume: 0.8,
);
```

### Playing a Specific Sound
```dart
await audioModule.playSpecific(
  'correct_1',
  audioModule.correctSounds,
);
```

### Looping a Sound
```dart
await audioModule.loopFromList(
  context,
  audioModule.levelUpSounds,
  volume: 0.5,
);
```

## Sound Control

### Volume Management
- Individual volume control
- Global mute state
- Volume persistence
- Volume restoration

### Playback Control
- Start playback
- Stop playback
- Pause playback
- Resume playback

## Resource Management
- Sound preloading
- Player cleanup
- Memory optimization
- Resource tracking

## Best Practices
1. Preload frequently used sounds
2. Manage sound categories
3. Control volume levels
4. Clean up resources
5. Handle errors gracefully

## Error Handling
- Playback errors
- Loading errors
- Resource errors
- State errors

## Dependencies
- `just_audio` package
- `shared_preferences`
- `Logger`

## Integration Points
The AudioModule integrates with:
- `ModuleManager`: For module access
- `ServicesManager`: For service access
- `SharedPreferences`: For state persistence

## Performance Considerations
- Sound preloading
- Memory usage
- Resource cleanup
- Playback optimization
- Battery impact

## State Management
- Mute state
- Volume state
- Playback state
- Resource state

## Accessibility
- Volume control
- Mute options
- Sound categories
- User preferences
- System settings 