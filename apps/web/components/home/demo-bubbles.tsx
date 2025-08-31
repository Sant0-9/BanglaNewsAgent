"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "../../lib/utils"
import { Bot, User } from "lucide-react"

interface DemoBubble {
  id: string
  type: 'user' | 'assistant'
  content: string
  contentBn: string
  delay: number
}

const demoBubbles: DemoBubble[] = [
  {
    id: '1',
    type: 'user',
    content: 'What\'s the latest news?',
    contentBn: 'সর্বশেষ খবর কী?',
    delay: 1
  },
  {
    id: '2', 
    type: 'assistant',
    content: 'Here are today\'s top headlines...',
    contentBn: 'আজকের প্রধান সংবাদগুলো হল...',
    delay: 2.5
  },
  {
    id: '3',
    type: 'user', 
    content: 'How\'s the weather today?',
    contentBn: 'আজ আবহাওয়া কেমন?',
    delay: 4
  },
  {
    id: '4',
    type: 'assistant',
    content: 'Today will be partly cloudy with...',
    contentBn: 'আজ আংশিক মেঘলা থাকবে...',
    delay: 5.5
  }
]

export function DemoBubbles() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)
  const [visibleBubbles, setVisibleBubbles] = useState<string[]>([])

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReducedMotion(mediaQuery.matches)
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches)
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  useEffect(() => {
    // Show bubbles with staggered delays
    const timeouts: NodeJS.Timeout[] = []
    
    demoBubbles.forEach((bubble) => {
      const timeout = setTimeout(() => {
        setVisibleBubbles(prev => [...prev, bubble.id])
      }, bubble.delay * 1000)
      timeouts.push(timeout)
    })

    // Reset after all bubbles are shown
    const resetTimeout = setTimeout(() => {
      setVisibleBubbles([])
    }, 10000)
    timeouts.push(resetTimeout)

    return () => timeouts.forEach(clearTimeout)
  }, [])

  const bubbleVariants = {
    hidden: {
      opacity: 0,
      y: 20,
      scale: 0.9
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        duration: 0.4,
        ease: [0.22, 1, 0.36, 1]
      }
    },
    exit: {
      opacity: 0,
      y: -10,
      scale: 0.95,
      transition: {
        duration: 0.3
      }
    }
  }

  return (
    <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 w-full max-w-md px-4">
      <div className="space-y-3">
        <AnimatePresence mode="popLayout">
          {demoBubbles
            .filter(bubble => visibleBubbles.includes(bubble.id))
            .map((bubble) => (
              <motion.div
                key={bubble.id}
                variants={prefersReducedMotion ? {} : bubbleVariants}
                initial={prefersReducedMotion ? {} : "hidden"}
                animate="visible"
                exit={prefersReducedMotion ? {} : "exit"}
                className={cn(
                  "flex gap-3",
                  bubble.type === 'user' ? "justify-end" : "justify-start"
                )}
              >
                {/* Avatar */}
                {bubble.type === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-lg">
                    <Bot className="h-4 w-4 text-white" />
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={cn(
                    "max-w-xs px-4 py-3 rounded-2xl shadow-lg backdrop-blur-xl",
                    bubble.type === 'user'
                      ? "bg-gradient-to-r from-primary to-accent text-primary-foreground"
                      : "bg-card/80 border border-border/50 text-foreground"
                  )}
                >
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-relaxed">
                      {bubble.contentBn}
                    </p>
                    <p className="text-xs opacity-80 leading-relaxed">
                      {bubble.content}
                    </p>
                  </div>
                </div>

                {/* User Avatar */}
                {bubble.type === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-fire-ember to-fire-gold flex items-center justify-center shadow-lg">
                    <User className="h-4 w-4 text-white" />
                  </div>
                )}
              </motion.div>
            ))}
        </AnimatePresence>
      </div>

      {/* Hint Text */}
      {visibleBubbles.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center mt-6"
        >
          <p className="text-sm text-muted-foreground">
            Watch the demo conversation above
          </p>
          <p className="text-xs text-muted-foreground/80 mt-1">
            উপরে ডেমো কথোপকথন দেখুন
          </p>
        </motion.div>
      )}
    </div>
  )
}