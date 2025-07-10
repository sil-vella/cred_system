# Theme Constants Documentation

## Overview
The theme constants provide a comprehensive theming system for the application, including color schemes, text styles, backgrounds, and component-specific styling. The system is built around a dark theme with accent colors and consistent styling across all UI elements.

## Key Features
- Dark theme implementation
- Consistent color palette
- Typography system
- Component styling
- Background assets
- Padding standards

## Class Structure

### AppColors
Static color constants for the application.

#### Properties
- `primaryColor`: Main theme color
- `accentColor`: Primary accent color
- `accentColor2`: Secondary accent color
- `scaffoldBackgroundColor`: Background color
- `white`: White color
- `darkGray`: Dark gray shade
- `lightGray`: Light gray shade
- `redAccent`: Error color

### AppBackgrounds
Background image asset paths.

#### Properties
- `backgrounds`: List of background image paths

### AppTextStyles
Text style definitions for the application.

#### Methods
- `headingLarge`: Large heading style
- `headingMedium`: Medium heading style
- `headingSmall`: Small heading style
- `bodyMedium`: Medium body text style
- `bodyLarge`: Large body text style
- `buttonText`: Button text style

### AppPadding
Standard padding measurements.

#### Properties
- `defaultPadding`: Default padding
- `cardPadding`: Card-specific padding

### AppTheme
Main theme configuration.

#### Methods
- `darkTheme`: Dark theme configuration

## Theme Components

### Color Scheme
```dart
static const Color primaryColor = Color(0xFF1C1B2E);
static const Color accentColor = Color(0xFF8A4090);
static const Color accentColor2 = Color(0xFFFBC02D);
```

### Typography
```dart
static TextStyle headingLarge({Color color = AppColors.accentColor}) {
  return TextStyle(
    fontSize: 28,
    fontWeight: FontWeight.bold,
    color: color,
  );
}
```

### Component Styling
- Button themes
- Input decoration
- Text selection
- Navigation elements
- Drawer styling

## Usage Examples

### Text Styles
```dart
Text(
  'Title',
  style: AppTextStyles.headingLarge(),
);
```

### Colors
```dart
Container(
  color: AppColors.primaryColor,
  child: Text('Content'),
);
```

### Padding
```dart
Padding(
  padding: AppPadding.defaultPadding,
  child: Widget(),
);
```

## Best Practices
1. Use predefined constants
2. Maintain color consistency
3. Follow typography hierarchy
4. Apply standard padding
5. Use theme components

## Theme Components
- Text styles
- Color scheme
- Button styles
- Input fields
- Navigation elements
- Cards and containers
- Selection styles

## Integration Points
The theme integrates with:
- Material components
- Custom widgets
- Navigation system
- Form elements
- Layout system

## Customization
- Color overrides
- Text style modifications
- Component styling
- Padding adjustments
- Background assets

## Performance Considerations
- Style caching
- Color opacity
- Asset management
- Theme inheritance
- Widget rebuilds

## Accessibility
- Color contrast
- Text scaling
- Touch targets
- Focus indicators
- Error states 