# Drawer Base Documentation

## Overview
The `drawer_base.dart` file provides a custom drawer implementation that integrates with the application's navigation system and theme. It automatically populates navigation items based on registered routes and provides a consistent UI experience.

## Key Features
- Dynamic route integration
- Theme-aware styling
- Custom background
- Responsive layout
- Navigation integration

## Class Structure

### CustomDrawer
A `StatelessWidget` that implements the application's drawer.

#### Properties
- None (uses context-based properties)

#### Methods
- `build`: Builds the drawer widget

## Usage Examples

### Basic Usage
```dart
Scaffold(
  drawer: CustomDrawer(),
  // ... rest of the scaffold
);
```

## Drawer Structure
1. Background
   - Primary color base
   - Semi-transparent overlay image
   - Custom opacity settings

2. Header
   - Title text
   - Custom styling
   - Bottom-aligned content

3. Navigation Items
   - Home item (fixed)
   - Dynamic route items
   - Icon and text styling
   - Tap handlers

## Styling Details
- Uses `AppColors` for consistent coloring
- Implements `AppTextStyles` for typography
- Custom background image support
- Responsive layout design

## Navigation Integration
- Uses `GoRouter` for navigation
- Integrates with `NavigationManager`
- Supports dynamic route updates
- Maintains navigation state

## Best Practices
1. Use consistent route registration
2. Provide proper drawer icons
3. Maintain route order
4. Handle navigation errors
5. Update routes as needed

## Dependencies
- `flutter/material.dart`
- `go_router/go_router.dart`
- `provider/provider.dart`
- `../../utils/consts/theme_consts.dart`
- `../managers/navigation_manager.dart`

## Theme Integration
- Primary color background
- Accent color icons
- Consistent text styles
- Custom background image
- Opacity controls

## Error Handling
- Route validation
- Navigation error prevention
- Empty route handling
- Icon presence checking

## Performance Considerations
- Efficient list building
- Minimal rebuilds
- Optimized image loading
- Proper state management

## Customization Options
- Background image
- Header content
- Icon colors
- Text styles
- Route ordering 