import { 
  Newspaper, 
  CloudSun, 
  TrendingUp, 
  Trophy, 
  Search,
  Home,
  type LucideIcon
} from "lucide-react"

export interface QuickPrompt {
  text: string
  icon: string
  category: string
}

export interface RouteConfig {
  id: string
  title: string
  path: string
  icon: LucideIcon
  banner: {
    gradient: string
    title: string
    description: string
    bgIcon: string
  }
  systemPrompt: string
  quickPrompts: QuickPrompt[]
}

export const routeConfigs: Record<string, RouteConfig> = {
  home: {
    id: 'home',
    title: 'General',
    path: '/',
    icon: Home,
    banner: {
      gradient: 'from-slate-600 to-slate-800',
      title: 'আপনার ব্যক্তিগত সংবাদ সহায়ক',
      description: 'সর্বশেষ সংবাদ, আবহাওয়া, শেয়ার বাজার এবং খেলাধুলার খবর পান আপনার ভাষায়',
      bgIcon: '🤖'
    },
    systemPrompt: 'You are KhoborAgent, a helpful AI assistant specialized in providing news, weather, market updates, and sports information in Bengali and English. Provide accurate, up-to-date information with proper sources.',
    quickPrompts: [
      { text: "আজকের সর্বশেষ খবর কী?", icon: "📰", category: "News" },
      { text: "বাংলাদেশের আর্থিক অবস্থা", icon: "💰", category: "Economy" },
      { text: "ঢাকার আবহাওয়া কেমন?", icon: "🌤️", category: "Weather" },
      { text: "ক্রিকেট ম্যাচের খবর", icon: "🏏", category: "Sports" },
    ]
  },
  
  news: {
    id: 'news',
    title: 'News',
    path: '/news',
    icon: Newspaper,
    banner: {
      gradient: 'from-red-600 to-red-800',
      title: 'সর্বশেষ সংবাদ',
      description: 'বাংলাদেশ ও বিশ্বের গুরুত্বপূর্ণ খবর পান তাৎক্ষণিক আপডেটের সাথে',
      bgIcon: '📰'
    },
    systemPrompt: 'You are a specialized news assistant. Focus on providing the latest news, breaking stories, political updates, and current events. Always cite reliable sources and provide context for news stories. Prioritize Bengali news sources when relevant.',
    quickPrompts: [
      { text: "আজকের প্রধান খবরগুলো কী?", icon: "🔥", category: "Breaking" },
      { text: "বাংলাদেশের রাজনৈতিক খবর", icon: "🏛️", category: "Politics" },
      { text: "আন্তর্জাতিক সংবাদ", icon: "🌍", category: "International" },
      { text: "স্থানীয় সংবাদ", icon: "📍", category: "Local" },
      { text: "টেকনোলজি সংবাদ", icon: "💻", category: "Technology" },
      { text: "শিক্ষা সংক্রান্ত খবর", icon: "🎓", category: "Education" }
    ]
  },

  weather: {
    id: 'weather',
    title: 'Weather', 
    path: '/weather',
    icon: CloudSun,
    banner: {
      gradient: 'from-amber-600 to-orange-600',
      title: 'আবহাওয়া পূর্বাভাস',
      description: 'বাংলাদেশের সকল বিভাগের আবহাওয়া, তাপমাত্রা এবং বৃষ্টিপাতের সম্ভাবনা',
      bgIcon: '🌤️'
    },
    systemPrompt: 'You are a weather specialist assistant. Provide detailed weather forecasts, temperature information, rainfall predictions, and weather-related advisories for Bangladesh and other locations. Include safety tips during extreme weather conditions.',
    quickPrompts: [
      { text: "ঢাকার আজকের আবহাওয়া", icon: "🌡️", category: "Current" },
      { text: "চট্টগ্রামের আবহাওয়া", icon: "🌊", category: "Regional" },
      { text: "সাপ্তাহিক আবহাওয়া পূর্বাভাস", icon: "📅", category: "Forecast" },
      { text: "বৃষ্টিপাতের সম্ভাবনা", icon: "🌧️", category: "Rain" },
      { text: "ঝড়ের পূর্বাভাস", icon: "⛈️", category: "Storm" },
      { text: "তাপপ্রবাহের সতর্কতা", icon: "🔥", category: "Heatwave" }
    ]
  },

  markets: {
    id: 'markets',
    title: 'Markets',
    path: '/markets', 
    icon: TrendingUp,
    banner: {
      gradient: 'from-green-600 to-emerald-600',
      title: 'শেয়ার বাজার ও অর্থনীতি',
      description: 'ঢাকা স্টক এক্সচেঞ্জ, আর্থিক সূচক এবং বাজার বিশ্লেষণ',
      bgIcon: '💹'
    },
    systemPrompt: 'You are a financial markets specialist. Provide stock market updates, economic indicators, financial analysis, and investment insights focusing on Dhaka Stock Exchange (DSE), Chittagong Stock Exchange (CSE), and global markets that affect Bangladesh economy.',
    quickPrompts: [
      { text: "DSE আজকের বাজার অবস্থা", icon: "📈", category: "DSE" },
      { text: "শীর্ষ গেইনার শেয়ার", icon: "🚀", category: "Gainers" },
      { text: "ব্যাংক সেক্টরের অবস্থা", icon: "🏦", category: "Banking" },
      { text: "ডলারের বিনিময় হার", icon: "💱", category: "Currency" },
      { text: "সোনার দাম", icon: "🪙", category: "Commodities" },
      { text: "মুদ্রাস্ফীতি পরিস্থিতি", icon: "📊", category: "Inflation" }
    ]
  },

  sports: {
    id: 'sports',
    title: 'Sports',
    path: '/sports',
    icon: Trophy,
    banner: {
      gradient: 'from-orange-600 to-red-600', 
      title: 'খেলাধুলার জগত',
      description: 'ক্রিকেট, ফুটবল এবং অন্যান্য খেলার সর্বশেষ খবর ও স্কোর',
      bgIcon: '🏏'
    },
    systemPrompt: 'You are a sports specialist assistant. Focus on cricket (especially Bangladesh team), football, and other sports popular in Bangladesh. Provide match updates, scores, player statistics, and sports news with enthusiasm and detailed analysis.',
    quickPrompts: [
      { text: "বাংলাদেশ ক্রিকেট দলের খবর", icon: "🏏", category: "Cricket" },
      { text: "আজকের ম্যাচের স্কোর", icon: "⚡", category: "Live" },
      { text: "প্রিমিয়ার লিগের খবর", icon: "⚽", category: "Football" },
      { text: "বিশ্বকাপের আপডেট", icon: "🏆", category: "World Cup" },
      { text: "স্থানীয় খেলার খবর", icon: "🥅", category: "Local" },
      { text: "অলিম্পিক আপডেট", icon: "🥇", category: "Olympics" }
    ]
  },

  lookup: {
    id: 'lookup',
    title: 'Lookup',
    path: '/lookup',
    icon: Search,
    banner: {
      gradient: 'from-yellow-600 to-amber-600',
      title: 'তথ্য অনুসন্ধান',
      description: 'যেকোনো বিষয়ে বিস্তারিত তথ্য, ইতিহাস এবং ব্যাখ্যা খুঁজুন',
      bgIcon: '🔍'
    },
    systemPrompt: 'You are a research and lookup specialist. Help users find detailed information, explanations, historical context, definitions, and comprehensive answers about any topic. Focus on accuracy and provide multiple perspectives when relevant.',
    quickPrompts: [
      { text: "বাংলাদেশের ইতিহাস", icon: "📚", category: "History" },
      { text: "বিজ্ঞান ও প্রযুক্তি", icon: "🔬", category: "Science" },
      { text: "সাহিত্য ও সংস্কৃতি", icon: "🎭", category: "Culture" },
      { text: "ভূগোল ও পরিবেশ", icon: "🌍", category: "Geography" },
      { text: "আইন ও নীতিমালা", icon: "⚖️", category: "Legal" },
      { text: "স্বাস্থ্য তথ্য", icon: "🏥", category: "Health" }
    ]
  }
}

export const getRouteConfig = (path: string): RouteConfig => {
  // Find config by path
  const config = Object.values(routeConfigs).find(config => config.path === path)
  return config || routeConfigs.home
}

export const getRouteByMode = (mode: string): RouteConfig => {
  return routeConfigs[mode] || routeConfigs.home
}

export const getAllRoutes = (): RouteConfig[] => {
  return Object.values(routeConfigs)
}