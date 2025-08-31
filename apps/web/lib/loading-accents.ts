export type RouteMode = 'news' | 'sports' | 'markets' | 'weather' | 'lookup' | 'general'

export interface AccentConfig {
  primary: string
  secondary: string
  glow: string
  particle: string
  name: string
}

const ACCENT_MAP: Record<RouteMode, AccentConfig> = {
  news: {
    primary: '#7C3AED',
    secondary: '#06B6D4',
    glow: 'rgba(124, 58, 237, 0.4)',
    particle: 'rgba(6, 182, 212, 0.6)',
    name: 'news'
  },
  sports: {
    primary: '#10B981',
    secondary: '#34D399',
    glow: 'rgba(16, 185, 129, 0.4)',
    particle: 'rgba(52, 211, 153, 0.6)',
    name: 'sports'
  },
  markets: {
    primary: '#3B82F6',
    secondary: '#1D4ED8',
    glow: 'rgba(59, 130, 246, 0.4)',
    particle: 'rgba(29, 78, 216, 0.6)',
    name: 'markets'
  },
  weather: {
    primary: '#06B6D4',
    secondary: '#0891B2',
    glow: 'rgba(6, 182, 212, 0.4)',
    particle: 'rgba(8, 145, 178, 0.6)',
    name: 'weather'
  },
  lookup: {
    primary: '#F59E0B',
    secondary: '#D97706',
    glow: 'rgba(245, 158, 11, 0.4)',
    particle: 'rgba(217, 119, 6, 0.6)',
    name: 'lookup'
  },
  general: {
    primary: '#7C3AED',
    secondary: '#06B6D4',
    glow: 'rgba(124, 58, 237, 0.4)',
    particle: 'rgba(6, 182, 212, 0.6)',
    name: 'general'
  }
}

/**
 * Get accent colors for a specific route mode
 * @param mode Route mode to get accents for
 * @returns AccentConfig object with all color variants
 */
export function routeAccent(mode: RouteMode = 'general'): AccentConfig {
  return ACCENT_MAP[mode] || ACCENT_MAP.general
}

/**
 * Get CSS custom properties string for dynamic styling
 * @param mode Route mode to get CSS properties for
 * @returns CSS custom properties string
 */
export function getAccentCSSProps(mode: RouteMode = 'general'): Record<string, string> {
  const accent = routeAccent(mode)
  return {
    '--accent-primary': accent.primary,
    '--accent-secondary': accent.secondary,
    '--accent-glow': accent.glow,
    '--accent-particle': accent.particle
  }
}

/**
 * Get gradient string for the specified mode
 * @param mode Route mode
 * @param direction Gradient direction (default: 'to right')
 * @returns CSS gradient string
 */
export function getAccentGradient(mode: RouteMode = 'general', direction = 'to right'): string {
  const accent = routeAccent(mode)
  return `linear-gradient(${direction}, ${accent.primary}, ${accent.secondary})`
}