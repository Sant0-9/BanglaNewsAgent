"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { useRouter } from "next/navigation"
import { Button } from "../ui/button"
import { FloatingLogo } from "./floating-logo"
import { cn } from "../../lib/utils"
import { 
  ArrowRight,
  Newspaper,
  CloudSun,
  TrendingUp,
  Trophy,
  Search,
  MessageSquare,
  Sparkles
} from "lucide-react"

interface ModeButton {
  id: string
  title: string
  titleBn: string
  path: string
  icon: React.ComponentType<{ className?: string }>
  gradient: string
  description: string
  descriptionBn: string
}

const modeButtons: ModeButton[] = [
  {
    id: 'news',
    title: 'News',
    titleBn: 'সংবাদ',
    path: '/news',
    icon: Newspaper,
    gradient: 'from-red-500 to-red-600',
    description: 'Latest news and updates',
    descriptionBn: 'সর্বশেষ সংবাদ ও আপডেট'
  },
  {
    id: 'weather',
    title: 'Weather',
    titleBn: 'আবহাওয়া',
    path: '/weather',
    icon: CloudSun,
    gradient: 'from-amber-500 to-orange-500',
    description: 'Weather forecasts',
    descriptionBn: 'আবহাওয়ার পূর্বাভাস'
  },
  {
    id: 'markets',
    title: 'Markets',
    titleBn: 'বাজার',
    path: '/markets',
    icon: TrendingUp,
    gradient: 'from-green-500 to-emerald-500',
    description: 'Stock market updates',
    descriptionBn: 'শেয়ার বাজারের খবর'
  },
  {
    id: 'sports',
    title: 'Sports',
    titleBn: 'খেলাধুলা',
    path: '/sports',
    icon: Trophy,
    gradient: 'from-orange-500 to-red-500',
    description: 'Sports news and scores',
    descriptionBn: 'খেলার খবর ও স্কোর'
  },
  {
    id: 'lookup',
    title: 'Lookup',
    titleBn: 'অনুসন্ধান',
    path: '/lookup',
    icon: Search,
    gradient: 'from-yellow-500 to-amber-600',
    description: 'Research and information',
    descriptionBn: 'গবেষণা ও তথ্য'
  }
]

export function PremiumHero() {
  const router = useRouter()
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReducedMotion(mediaQuery.matches)
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches)
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  const handleStartChat = () => {
    router.push('/news')
  }

  const handleModeSelect = (path: string) => {
    router.push(path as any)
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-charcoal-950 via-charcoal-900 to-charcoal-800" />
      
      {/* Ambient Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-1/4 w-96 h-96 bg-gradient-to-r from-fire-molten/5 to-fire-ember/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-1/4 w-96 h-96 bg-gradient-to-l from-fire-ember/5 to-fire-gold/5 rounded-full blur-3xl" />
        <div className="absolute top-3/4 left-1/3 w-64 h-64 bg-gradient-to-br from-fire-amber/3 to-fire-molten/3 rounded-full blur-2xl" />
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-6 py-16 text-center">
        
        {/* Logo Section */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ 
            duration: 0.8, 
            ease: [0.22, 1, 0.36, 1] 
          }}
          className="mb-12"
        >
          <FloatingLogo size="xl" showRipples={!prefersReducedMotion} />
        </motion.div>

        {/* Title and Taglines */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ 
            duration: 0.8, 
            delay: 0.2,
            ease: [0.22, 1, 0.36, 1] 
          }}
          className="mb-8 max-w-4xl mx-auto"
        >
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold mb-6 leading-tight">
            <span className="bg-gradient-to-r from-fire-gold via-fire-amber to-fire-ember bg-clip-text text-transparent">
              KhoborAgent
            </span>
          </h1>
          
          <div className="space-y-3">
            <p className="text-xl md:text-2xl text-foreground/90 font-medium">
              আপনার ব্যক্তিগত AI সংবাদ সহায়ক
            </p>
            <p className="text-lg md:text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
              Your personal AI news assistant for the latest updates in Bengali and English
            </p>
          </div>
        </motion.div>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ 
            duration: 0.8, 
            delay: 0.4,
            ease: [0.22, 1, 0.36, 1] 
          }}
          className="mb-16"
        >
          <Button
            onClick={handleStartChat}
            size="lg"
            className="px-8 py-6 text-lg font-medium bg-gradient-to-r from-fire-molten to-fire-ember hover:opacity-90 hover:shadow-fire-molten/25 shadow-lg hover:shadow-xl transition-all duration-300 group relative overflow-hidden"
          >
            {/* Fiery aura effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-fire-gold/20 to-fire-ember/20 animate-pulse-glow" />
            <div className="relative z-10 flex items-center">
              <MessageSquare className="mr-2 h-5 w-5" />
              Start Chatting
              <span className="ml-2 text-sm opacity-75">চ্যাট শুরু করুন</span>
              <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </Button>
        </motion.div>

        {/* Mode Selection Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ 
            duration: 1, 
            delay: 0.6,
            ease: [0.22, 1, 0.36, 1] 
          }}
          className="w-full max-w-6xl mx-auto"
        >
          <h2 className="text-2xl md:text-3xl font-bold mb-8 bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text text-transparent">
            Choose Your Topic
            <span className="block text-lg font-medium text-muted-foreground mt-2">
              আপনার বিষয় নির্বাচন করুন
            </span>
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {modeButtons.map((mode, index) => (
              <motion.button
                key={mode.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ 
                  duration: 0.6, 
                  delay: 0.8 + index * 0.1,
                  ease: [0.22, 1, 0.36, 1] 
                }}
                whileHover={{ 
                  scale: prefersReducedMotion ? 1 : 1.02,
                  y: prefersReducedMotion ? 0 : -2
                }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleModeSelect(mode.path)}
                className={cn(
                  "group relative p-6 rounded-2xl border border-border/50 bg-card/50 backdrop-blur-xl",
                  "hover:border-border hover:bg-card/80 hover:shadow-xl transition-all duration-300",
                  "text-left focus:outline-none focus:ring-2 focus:ring-primary/50"
                )}
              >
                {/* Background Gradient on Hover */}
                <div className={cn(
                  "absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-5 transition-opacity duration-300",
                  `bg-gradient-to-br ${mode.gradient}`
                )} />
                
                <div className="relative z-10">
                  <div className="flex items-center gap-4 mb-3">
                    <div className={cn(
                      "w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300",
                      `bg-gradient-to-br ${mode.gradient} text-white shadow-lg`,
                      "group-hover:scale-110 group-hover:shadow-xl"
                    )}>
                      <mode.icon className="h-6 w-6" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-foreground group-hover:text-primary transition-colors">
                        {mode.title}
                      </h3>
                      <p className="text-base font-medium text-foreground/80">
                        {mode.titleBn}
                      </p>
                    </div>
                  </div>
                  
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">
                      {mode.description}
                    </p>
                    <p className="text-sm text-muted-foreground/80">
                      {mode.descriptionBn}
                    </p>
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  )
}