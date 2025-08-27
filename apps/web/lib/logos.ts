/**
 * Logo mapping for well-known news sources and organizations
 * Maps source names to placeholder logo URLs (SVG/PNG)
 */

export const SOURCE_LOGOS: Record<string, string> = {
  // International News
  "Reuters": "https://via.placeholder.com/32x32/0066cc/ffffff?text=R",
  "AP": "https://via.placeholder.com/32x32/e31e24/ffffff?text=AP",
  "BBC": "https://via.placeholder.com/32x32/bb1919/ffffff?text=BBC",
  "CNN": "https://via.placeholder.com/32x32/cc0000/ffffff?text=CNN",
  "Al Jazeera": "https://via.placeholder.com/32x32/f59e0b/ffffff?text=AJ",
  "Associated Press": "https://via.placeholder.com/32x32/e31e24/ffffff?text=AP",
  
  // Bangladeshi News
  "Dhaka Tribune": "https://via.placeholder.com/32x32/1f2937/ffffff?text=DT",
  "The Daily Star": "https://via.placeholder.com/32x32/dc2626/ffffff?text=DS",
  "bdnews24": "https://via.placeholder.com/32x32/059669/ffffff?text=BD",
  "Prothom Alo": "https://via.placeholder.com/32x32/1e40af/ffffff?text=PA",
  "New Age": "https://via.placeholder.com/32x32/7c3aed/ffffff?text=NA",
  "The Business Standard": "https://via.placeholder.com/32x32/0891b2/ffffff?text=BS",
  
  // Tech News
  "TechCrunch": "https://via.placeholder.com/32x32/00d084/ffffff?text=TC",
  "The Verge": "https://via.placeholder.com/32x32/ff6900/ffffff?text=TV",
  "Ars Technica": "https://via.placeholder.com/32x32/ff4500/ffffff?text=AT",
  "Wired": "https://via.placeholder.com/32x32/000000/ffffff?text=W",
  "Engadget": "https://via.placeholder.com/32x32/00bcd4/ffffff?text=E",
  
  // Financial News
  "Yahoo Finance": "https://via.placeholder.com/32x32/7b68ee/ffffff?text=YF",
  "Bloomberg": "https://via.placeholder.com/32x32/1a1a1a/ffffff?text=B",
  "Financial Times": "https://via.placeholder.com/32x32/ff9800/ffffff?text=FT",
  "Wall Street Journal": "https://via.placeholder.com/32x32/0066cc/ffffff?text=WSJ",
  "MarketWatch": "https://via.placeholder.com/32x32/0d7377/ffffff?text=MW",
  
  // Weather Services
  "OpenWeatherMap": "https://via.placeholder.com/32x32/4fc3f7/ffffff?text=OW",
  "Weather.com": "https://via.placeholder.com/32x32/0288d1/ffffff?text=W",
  "AccuWeather": "https://via.placeholder.com/32x32/ff8a65/ffffff?text=AW",
  
  // Stock/Markets
  "Alpha Vantage": "https://via.placeholder.com/32x32/4caf50/ffffff?text=AV",
  "Yahoo Finance API": "https://via.placeholder.com/32x32/7b68ee/ffffff?text=YF",
  "IEX Cloud": "https://via.placeholder.com/32x32/6366f1/ffffff?text=IEX",
  
  // Sports
  "ESPN": "https://via.placeholder.com/32x32/d32f2f/ffffff?text=ESPN",
  "BBC Sport": "https://via.placeholder.com/32x32/bb1919/ffffff?text=BBC",
  "Sky Sports": "https://via.placeholder.com/32x32/1565c0/ffffff?text=SKY",
  
  // Reference/Lookup
  "Wikipedia": "https://via.placeholder.com/32x32/6b7280/ffffff?text=W",
  "Britannica": "https://via.placeholder.com/32x32/8b5cf6/ffffff?text=B",
};

/**
 * Get logo URL for a given source name
 * @param sourceName - Name of the source
 * @returns Logo URL or default placeholder
 */
export function getSourceLogo(sourceName: string): string {
  // Try exact match first
  if (SOURCE_LOGOS[sourceName]) {
    return SOURCE_LOGOS[sourceName];
  }
  
  // Try case-insensitive partial matching
  const normalizedName = sourceName.toLowerCase();
  for (const [key, logo] of Object.entries(SOURCE_LOGOS)) {
    if (key.toLowerCase().includes(normalizedName) || normalizedName.includes(key.toLowerCase())) {
      return logo;
    }
  }
  
  // Default placeholder with first letter of source name
  const firstLetter = sourceName.charAt(0).toUpperCase() || "?";
  return `https://via.placeholder.com/32x32/6b7280/ffffff?text=${encodeURIComponent(firstLetter)}`;
}

/**
 * Get multiple logos for a list of source names
 */
export function getSourceLogos(sourceNames: string[]): Record<string, string> {
  return sourceNames.reduce((acc, name) => {
    acc[name] = getSourceLogo(name);
    return acc;
  }, {} as Record<string, string>);
}

/**
 * Check if a source has a known logo
 */
export function hasKnownLogo(sourceName: string): boolean {
  return sourceName in SOURCE_LOGOS;
}

/**
 * Get all available source names with logos
 */
export function getAvailableSourceNames(): string[] {
  return Object.keys(SOURCE_LOGOS);
}