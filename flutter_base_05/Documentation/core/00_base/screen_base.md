# Screen Base Documentation

## Overview
The `screen_base.dart` file provides a comprehensive base structure for creating screens in the application. It includes abstract base classes and utility widgets that implement common UI patterns and styling.

## Key Features
- Abstract base screen class
- Pre-built UI components
- Consistent styling
- Banner ad integration
- Responsive layout support
- Theme integration

## Classes

### BaseScreen
An abstract `StatefulWidget` that serves as the base for all screens.

#### Properties
- `Key? key`: Widget key

#### Methods
- `computeTitle`: Abstract method for dynamic title computation
- `getAppBarActions`: Optional method for app bar actions
- `getAppBar`: Optional method for custom app bar
- `getFloatingActionButton`: Optional method for FAB
- `getBottomNavigationBar`: Optional method for bottom nav
- `getBackground`: Optional method for custom background
- `getContentPadding`: Optional method for content padding
- `getContentMargin`: Optional method for content margin
- `getContentAlignment`: Optional method for content alignment
- `getContentCrossAlignment`: Optional method for cross alignment
- `getContentMainAxisSize`: Optional method for main axis size

### BaseScreenState
The state class for `BaseScreen` that provides UI building methods.

#### Properties
- `appManager`: App manager instance
- `_moduleManager`: Module manager instance
- `log`: Logger instance
- `bannerAdModule`: Banner ad module instance

#### Methods
- `buildHeader`: Builds a header container
- `buildContentCard`: Builds a styled content card
- `buildListTile`: Builds a styled list tile
- `buildRow`: Builds a row with custom alignment
- `buildButtonRow`: Builds a row of buttons
- `buildExpandedRow`: Builds a row with expanded children
- `buildFormField`: Builds a styled form field
- `buildLoadingIndicator`: Builds a loading indicator
- `buildErrorView`: Builds an error view
- `buildSectionTitle`: Builds a section title
- `buildDivider`: Builds a styled divider
- `buildSpacer`: Builds a spacing widget
- `buildContent`: Abstract method for main content

### BaseCard
A styled card widget for consistent UI.

#### Properties
- `child`: Card content
- `margin`: Optional margin
- `padding`: Optional padding

### BaseButton
A styled button widget with icon support.

#### Properties
- `text`: Button text
- `onPressed`: Press callback
- `isPrimary`: Primary style flag
- `isFullWidth`: Full width flag
- `icon`: Optional icon

### BaseTextField
A styled text field widget.

#### Properties
- `controller`: Text controller
- `label`: Field label
- `hint`: Optional hint text
- `obscureText`: Password field flag
- `readOnly`: Read-only flag
- `maxLines`: Maximum lines
- `keyboardType`: Input type
- `validator`: Validation function
- `onChanged`: Change callback

## Usage Examples

### Creating a Screen
```dart
class MyScreen extends BaseScreen {
  @override
  String computeTitle(BuildContext context) => 'My Screen';

  @override
  BaseScreenState createState() => _MyScreenState();
}

class _MyScreenState extends BaseScreenState<MyScreen> {
  @override
  Widget buildContent(BuildContext context) {
    return buildContentCard(
      context,
      child: Column(
        children: [
          buildSectionTitle('My Section'),
          buildFormField(
        label: 'Username',
        controller: TextEditingController(),
      ),
    ),
  );
}
```

### Using Base Components
```dart
// Using BaseCard
BaseCard(
  child: Text('Card Content'),
);

// Using BaseButton
BaseButton(
  text: 'Click Me',
  onPressed: () {},
  icon: Icons.add,
);

// Using BaseTextField
BaseTextField(
  controller: TextEditingController(),
  label: 'Username',
);
```

## Styling and Theme
- Consistent color scheme
- Predefined text styles
- Standardized padding and margins
- Responsive layout support
- Theme-aware components

## Banner Ad Integration
- Automatic banner ad loading
- Top and bottom banner support
- Configurable ad units
- Error handling

## Best Practices
1. Extend BaseScreen for new screens
2. Use provided base components
3. Implement required abstract methods
4. Follow theme guidelines
5. Handle errors appropriately

## Dependencies
- `flutter/material.dart`
- `provider/provider.dart`
- `../../tools/logging/logger.dart`
- `../managers/app_manager.dart`
- `../managers/module_manager.dart`
- `../managers/navigation_manager.dart`
- `../../utils/consts/config.dart`
- `../../utils/consts/theme_consts.dart`
- `drawer_base.dart`

## Layout Structure
1. App Bar
2. Banner Ad (optional)
3. Main Content
   - Automatically scrollable
   - Minimum height constraint to fill available space
   - Content can exceed minimum height
4. Banner Ad (optional)
5. Bottom Navigation (optional)

## Content Scrolling
The main content area is automatically wrapped in a `SingleChildScrollView` with the following features:
- Minimum height constraint to fill available space
- Scrollable when content exceeds available height
- Maintains consistent layout even with minimal content
- Handles overflow gracefully

## Error Handling
- Loading indicators
- Error views
- Validation support
- Logging integration 