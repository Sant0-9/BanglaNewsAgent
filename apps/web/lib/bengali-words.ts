// Curated list of short Bengali news words (nouns and verbs)
// Selected for readability and relevance to news content

export interface BengaliWord {
  bn: string      // Bengali text
  en: string      // English translation  
  type: 'noun' | 'verb'
  category: 'politics' | 'economy' | 'sports' | 'weather' | 'general'
}

export const bengaliNewsWords: BengaliWord[] = [
  // Politics & Government
  { bn: 'সংবাদ', en: 'news', type: 'noun', category: 'general' },
  { bn: 'নির্বাচন', en: 'election', type: 'noun', category: 'politics' },
  { bn: 'সরকার', en: 'government', type: 'noun', category: 'politics' },
  { bn: 'প্রধানমন্ত্রী', en: 'prime minister', type: 'noun', category: 'politics' },
  { bn: 'রাষ্ট্রপতি', en: 'president', type: 'noun', category: 'politics' },
  { bn: 'সংসদ', en: 'parliament', type: 'noun', category: 'politics' },
  { bn: 'আইন', en: 'law', type: 'noun', category: 'politics' },
  { bn: 'নীতি', en: 'policy', type: 'noun', category: 'politics' },
  { bn: 'দল', en: 'party', type: 'noun', category: 'politics' },
  { bn: 'নেতা', en: 'leader', type: 'noun', category: 'politics' },
  
  // Economy & Business
  { bn: 'অর্থনীতি', en: 'economy', type: 'noun', category: 'economy' },
  { bn: 'বাজার', en: 'market', type: 'noun', category: 'economy' },
  { bn: 'ব্যাংক', en: 'bank', type: 'noun', category: 'economy' },
  { bn: 'টাকা', en: 'money', type: 'noun', category: 'economy' },
  { bn: 'ব্যবসা', en: 'business', type: 'noun', category: 'economy' },
  { bn: 'কোম্পানি', en: 'company', type: 'noun', category: 'economy' },
  { bn: 'বিনিয়োগ', en: 'investment', type: 'noun', category: 'economy' },
  { bn: 'রপ্তানি', en: 'export', type: 'noun', category: 'economy' },
  { bn: 'আমদানি', en: 'import', type: 'noun', category: 'economy' },
  { bn: 'মূল্য', en: 'price', type: 'noun', category: 'economy' },
  
  // Sports
  { bn: 'ক্রিকেট', en: 'cricket', type: 'noun', category: 'sports' },
  { bn: 'ফুটবল', en: 'football', type: 'noun', category: 'sports' },
  { bn: 'খেলা', en: 'game', type: 'noun', category: 'sports' },
  { bn: 'ম্যাচ', en: 'match', type: 'noun', category: 'sports' },
  { bn: 'দল', en: 'team', type: 'noun', category: 'sports' },
  { bn: 'খেলোয়াড়', en: 'player', type: 'noun', category: 'sports' },
  { bn: 'জিত', en: 'win', type: 'noun', category: 'sports' },
  { bn: 'হার', en: 'loss', type: 'noun', category: 'sports' },
  { bn: 'গোল', en: 'goal', type: 'noun', category: 'sports' },
  { bn: 'রান', en: 'run', type: 'noun', category: 'sports' },
  
  // Weather
  { bn: 'আবহাওয়া', en: 'weather', type: 'noun', category: 'weather' },
  { bn: 'বৃষ্টি', en: 'rain', type: 'noun', category: 'weather' },
  { bn: 'ঝড়', en: 'storm', type: 'noun', category: 'weather' },
  { bn: 'গরম', en: 'heat', type: 'noun', category: 'weather' },
  { bn: 'ঠান্ডা', en: 'cold', type: 'noun', category: 'weather' },
  { bn: 'মেঘ', en: 'cloud', type: 'noun', category: 'weather' },
  { bn: 'রোদ', en: 'sun', type: 'noun', category: 'weather' },
  { bn: 'বন্যা', en: 'flood', type: 'noun', category: 'weather' },
  
  // General/Common
  { bn: 'মানুষ', en: 'people', type: 'noun', category: 'general' },
  { bn: 'দেশ', en: 'country', type: 'noun', category: 'general' },
  { bn: 'শহর', en: 'city', type: 'noun', category: 'general' },
  { bn: 'গ্রাম', en: 'village', type: 'noun', category: 'general' },
  { bn: 'স্কুল', en: 'school', type: 'noun', category: 'general' },
  { bn: 'হাসপাতাল', en: 'hospital', type: 'noun', category: 'general' },
  { bn: 'রাস্তা', en: 'road', type: 'noun', category: 'general' },
  { bn: 'পুলিশ', en: 'police', type: 'noun', category: 'general' },
  { bn: 'আগুন', en: 'fire', type: 'noun', category: 'general' },
  { bn: 'পানি', en: 'water', type: 'noun', category: 'general' },
  
  // Action Verbs
  { bn: 'বলা', en: 'say', type: 'verb', category: 'general' },
  { bn: 'করা', en: 'do', type: 'verb', category: 'general' },
  { bn: 'যাওয়া', en: 'go', type: 'verb', category: 'general' },
  { bn: 'আসা', en: 'come', type: 'verb', category: 'general' },
  { bn: 'দেখা', en: 'see', type: 'verb', category: 'general' },
  { bn: 'শোনা', en: 'hear', type: 'verb', category: 'general' },
  { bn: 'খাওয়া', en: 'eat', type: 'verb', category: 'general' },
  { bn: 'পড়া', en: 'read', type: 'verb', category: 'general' },
  { bn: 'লেখা', en: 'write', type: 'verb', category: 'general' },
  { bn: 'কাজ', en: 'work', type: 'noun', category: 'general' },
  
  // News-specific verbs
  { bn: 'ঘটা', en: 'happen', type: 'verb', category: 'general' },
  { bn: 'বৃদ্ধি', en: 'increase', type: 'verb', category: 'economy' },
  { bn: 'কমা', en: 'decrease', type: 'verb', category: 'general' },
  { bn: 'শুরু', en: 'start', type: 'verb', category: 'general' },
  { bn: 'শেষ', en: 'end', type: 'verb', category: 'general' },
  { bn: 'জেতা', en: 'win', type: 'verb', category: 'sports' },
  { bn: 'হারা', en: 'lose', type: 'verb', category: 'sports' },
  { bn: 'নেওয়া', en: 'take', type: 'verb', category: 'general' },
  { bn: 'দেওয়া', en: 'give', type: 'verb', category: 'general' },
  { bn: 'চালু', en: 'launch', type: 'verb', category: 'general' }
]

// Helper function to get random words by category
export function getWordsByCategory(category: BengaliWord['category'], count: number): BengaliWord[] {
  const filtered = bengaliNewsWords.filter(word => word.category === category)
  const shuffled = [...filtered].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, count)
}

// Helper function to get random words
export function getRandomWords(count: number): BengaliWord[] {
  const shuffled = [...bengaliNewsWords].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, count)
}

// Get word distribution for balanced display
export function getBalancedWords(totalCount: number): BengaliWord[] {
  const categories: BengaliWord['category'][] = ['politics', 'economy', 'sports', 'weather', 'general']
  const wordsPerCategory = Math.floor(totalCount / categories.length)
  const extraWords = totalCount % categories.length
  
  let result: BengaliWord[] = []
  
  categories.forEach((category, index) => {
    const count = wordsPerCategory + (index < extraWords ? 1 : 0)
    result = [...result, ...getWordsByCategory(category, count)]
  })
  
  // Fill remaining slots with random words if needed
  while (result.length < totalCount) {
    const remaining = bengaliNewsWords.filter(word => !result.includes(word))
    if (remaining.length === 0) break
    result.push(remaining[Math.floor(Math.random() * remaining.length)])
  }
  
  return result.slice(0, totalCount)
}