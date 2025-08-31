"use client"

import { motion, AnimatePresence } from "framer-motion"
import { useEffect, useState } from "react"
import { cn } from "../../lib/utils"
import { routeAccent, type RouteMode } from "../../lib/loading-accents"
import { 
  MessageSquare, 
  Loader2, 
  Sparkles,
  Bot
} from "lucide-react"

export interface GeneratingIndicatorProps {
  isVisible: boolean
  mode?: RouteMode
  className?: string
  messageId?: string
}

export function GeneratingIndicator({
  isVisible,
  mode = 'general',
  className,
  messageId
}: GeneratingIndicatorProps) {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)
  const [dots, setDots] = useState("")
  
  const accent = routeAccent(mode)

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReducedMotion(mediaQuery.matches)
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches)
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  // Animate dots for text-based loading indicator
  useEffect(() => {
    if (prefersReducedMotion || !isVisible) {
      setDots("...")
      return
    }

    let count = 0
    const interval = setInterval(() => {
      count = (count + 1) % 4
      setDots(".".repeat(count))
    }, 500)

    return () => clearInterval(interval)
  }, [prefersReducedMotion, isVisible])

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, x: -10, scale: 0.9 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: 10, scale: 0.9 }}
          transition={{ 
            duration: 0.2,
            ease: [0.22, 1, 0.36, 1]
          }}
          className={cn(
            "inline-flex items-center gap-2 px-3 py-1.5 rounded-full",
            "bg-card/90 backdrop-blur-sm border border-border/50",
            "shadow-lg text-sm font-medium",
            className
          )}
          data-message-id={messageId}
          aria-live="polite"
          aria-label="Generating answer"
          role="status"
        >
          {/* Animated Icon */}
          <motion.div
            className="relative flex items-center justify-center"
            animate={prefersReducedMotion ? {} : {
              rotate: [0, 360],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "linear"
            }}
          >
            {prefersReducedMotion ? (
              <Bot 
                className="h-4 w-4"
                style={{ color: accent.primary }}
              />
            ) : (
              <Loader2 
                className="h-4 w-4" 
                style={{ color: accent.primary }}
              />
            )}
          </motion.div>

          {/* Status Text */}
          <motion.span
            className="text-foreground select-none"
            animate={prefersReducedMotion ? {} : {
              opacity: [0.7, 1, 0.7]
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          >
            Generating answer{dots}
          </motion.span>

          {/* Bengali Text */}
          <motion.span
            className="text-muted-foreground text-xs select-none hidden sm:inline"
            animate={prefersReducedMotion ? {} : {
              opacity: [0.5, 0.8, 0.5]
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
              delay: 0.5
            }}
          >
            উত্তর তৈরি করা হচ্ছে{dots}
          </motion.span>

          {/* Glow Effect */}
          {!prefersReducedMotion && (
            <motion.div
              className="absolute inset-0 rounded-full pointer-events-none"
              animate={{
                boxShadow: [
                  `0 0 0 0 ${accent.glow}`,
                  `0 0 8px 2px ${accent.glow}`,
                  `0 0 0 0 ${accent.glow}`
                ]
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          )}

          {/* Sparkle Particles */}
          {!prefersReducedMotion && (
            <div className="absolute inset-0 pointer-events-none">
              {[...Array(3)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute"
                  style={{
                    left: `${20 + i * 30}%`,
                    top: `${10 + i * 20}%`
                  }}
                  animate={{
                    scale: [0, 1, 0],
                    rotate: [0, 180, 360],
                    opacity: [0, 0.8, 0]
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    delay: i * 0.3,
                    ease: "easeInOut"
                  }}
                >
                  <Sparkles 
                    className="h-2 w-2" 
                    style={{ color: accent.secondary }}
                  />
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}