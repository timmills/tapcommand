# Control Demo Page - Glassmorphism UI

A vibrant, modern control interface designed for tablet use in pub/club environments.

## Features

### 🎨 Multiple Themes
Choose from 5 professionally designed themes:

1. **Neon Club** - Vibrant pink and purple for high-energy venues
2. **Sports Bar** - Electric blue and orange for sports venues
3. **Premium Lounge** - Sophisticated gold and deep slate
4. **Sunset Lounge** - Warm sunset colors for relaxed atmosphere
5. **Ocean Breeze** - Cool teal and cyan for coastal venues

### ✨ Design Highlights

- **Glassmorphism Design**: Frosted glass effect with backdrop blur
- **Large Touch Targets**: 56px minimum height for all interactive elements
- **Animated Gradients**: Smooth color transitions in backgrounds
- **Glowing Status Indicators**: Animated power state indicators
- **Quick Actions**: Power, Volume, and Mute buttons on each card
- **Location-Based Grouping**: Collapsible sections by area
- **Real-time Selection**: Multi-select with visual feedback
- **Responsive Grid**: 2-4 columns depending on screen size

### 🎯 Touch-Optimized Features

- **Smooth animations** on all interactions
- **Scale feedback** on button press (active:scale-95)
- **Hover effects** with gradient overlays
- **Clear visual hierarchy** with bold typography
- **High contrast** for bright bar environments

## Access

Navigate to: **http://localhost:5173/control-demo**

Or in production: **http://100.93.158.19:5173/control-demo**

## Usage

### Theme Selection
- Click the theme button in the top-left corner
- Choose from 5 pre-designed themes
- Theme changes instantly across the entire interface

### Device Control
- **Click a device card** to select/deselect
- **Use quick action buttons** for immediate control (Power, Vol+, Mute)
- **Select multiple devices** for bulk operations
- **Use location headers** to control entire areas at once

### Bulk Operations
- Select devices by clicking cards
- Use location "Select All" buttons for quick selection
- Click the floating action button (bottom-right) to change channels
- Power on/off entire locations with header buttons

## File Structure

```
frontend-v2/src/features/control/
├── types/
│   └── themes.ts                        # Theme definitions
├── components/
│   ├── theme-selector.tsx              # Theme picker component
│   └── glassmorphic-device-card.tsx    # Enhanced device card
└── pages/
    ├── control-page.tsx                 # Original control page
    └── control-demo-page.tsx            # New glassmorphism demo
```

## Customization

### Adding New Themes

Edit `frontend-v2/src/features/control/types/themes.ts`:

```typescript
{
  id: 'my-theme',
  name: 'My Theme',
  description: 'Theme description',
  colors: {
    gradientFrom: '#color1',
    gradientVia: '#color2',
    gradientTo: '#color3',
    cardBg: 'rgba(255, 255, 255, 0.1)',
    cardBorder: 'rgba(255, 255, 255, 0.2)',
    // ... other colors
  },
}
```

### Adjusting Touch Target Sizes

Search for `min-h-[56px]` in component files and adjust as needed. Minimum recommended: 44px (iOS), 48px (Material).

## Performance

- Uses React.memo and useMemo for optimized rendering
- Virtual scrolling ready for 100+ devices
- Debounced API calls for bulk operations
- Optimistic UI updates

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Supports backdrop-filter (glassmorphism)

## Notes

- Original control page preserved at `/control`
- Demo page uses same data sources and APIs
- All existing functionality maintained
- Theme preference not persisted (future enhancement)

## Future Enhancements

- [ ] Save theme preference to localStorage
- [ ] Add more theme customization options
- [ ] Swipe gestures for quick actions
- [ ] Haptic feedback on supported devices
- [ ] Custom theme builder UI
- [ ] Dark/light mode toggle per theme
- [ ] Animation speed settings
