# Particle Systems & Text Field

This directory contains optimized instanced particle systems and Bengali text field for the HeroCanvas.

## Systems

### EmberParticles
- **Type**: Additive blending with warm colors
- **Animation**: Slow updraft with size flickering
- **Colors**: Fire-themed (#FF4D00 molten → #FF7A1A ember)
- **Features**: Size variation, opacity fade, lifecycle management

### DustParticles  
- **Type**: Normal blending with neutral colors
- **Animation**: Slow random drift
- **Colors**: Neutral whites with subtle variation
- **Features**: Tiny size, subtle sparkle effect

### BanglaWordField
- **Type**: SDF text sprites with troika-three-text
- **Animation**: Slow sine float, tiny yaw rotation, rare glow pulse
- **Layers**: 3-depth system (near/mid/far) with different scales and opacity
- **Content**: Curated Bengali news words (nouns/verbs)
- **Colors**: Fire-themed (gold for verbs, ember for nouns)

## Performance Tiers

### Desktop/Tablet Counts:
- **High**: 3,500 total (1,500 embers + 1,200 dust + 800 Bengali words)
- **Medium**: 1,800 total (800 embers + 600 dust + 400 Bengali words)  
- **Low**: 700 total (300 embers + 250 dust + 150 Bengali words)
- **Battery**: 330 total (150 embers + 100 dust + 80 Bengali words)

### Mobile Counts (much lower):
- **High**: 215 total (100 embers + 75 dust + 40 Bengali words)
- **Medium**: 150 total (75 embers + 50 dust + 25 Bengali words)
- **Low**: 95 total (50 embers + 30 dust + 15 Bengali words)
- **Battery**: 48 total (25 embers + 15 dust + 8 Bengali words)

## Performance Optimizations

1. **Instanced rendering** - Single draw call per particle system
2. **Shader-based animation** - GPU-accelerated movement
3. **SDF text rendering** - Scalable Distance Field fonts for crisp text
4. **Level-of-detail** - Performance-based update skipping  
5. **Mobile detection** - Aggressive element count reduction
6. **React.memo** - Prevents unnecessary re-renders
7. **Depth-based layering** - Proper z-ordering for visual depth
8. **UI collision avoidance** - Text positioned outside main UI areas
9. **Blending optimization** - Reduced opacity to prevent overbloom
10. **Memory management** - Efficient buffer and text caching

## Target Performance
- **Desktop**: 60 FPS minimum
- **Mobile**: 45+ FPS minimum
- **Text legibility**: Words readable when animation paused
- **UI dominance**: Text never overwhelms main interface
- **Overbloom**: Prevented via opacity limits and blending control

## Bengali Word Categories
- **Politics**: সংবাদ, নির্বাচন, সরকার, নেতা, আইন
- **Economy**: অর্থনীতি, বাজার, ব্যাংক, টাকা, ব্যবসা  
- **Sports**: ক্রিকেট, ফুটবল, খেলা, ম্যাচ, জিত
- **Weather**: আবহাওয়া, বৃষ্টি, ঝড়, মেঘ, রোদ
- **General**: মানুষ, দেশ, শহর, কাজ, সংবাদ