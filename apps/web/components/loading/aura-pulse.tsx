"use client"

import { motion } from "framer-motion"
import { useEffect, useState } from "react"
import { routeAccent, type RouteMode } from "../../lib/loading-accents"
import { cn } from "../../lib/utils"

export interface AuraPulseProps {
  mode?: RouteMode
  className?: string
}

export function AuraPulse({ mode = 'general', className }: AuraPulseProps) {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)
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

  // Animation variants for the pulsing effect
  const pulseVariants = {
    initial: {
      scale: 0.8,
      opacity: 0.4
    },
    animate: {
      scale: [0.8, 1.2, 0.9, 1.1, 0.8],
      opacity: [0.4, 0.8, 0.5, 0.7, 0.4],
      transition: {
        duration: 3.5,
        repeat: Infinity,
        ease: [0.4, 0, 0.6, 1]
      }
    },
    reduced: {
      scale: 1,
      opacity: 0.6
    }
  }

  return (
    <div 
      className={cn(
        "absolute pointer-events-none",
        className
      )}
      style={{
        width: '280px',
        height: '280px',
        transform: 'translate(-50%, -50%)',
        top: '50%',
        left: '50%'
      }}
    >
      {/* Main Aura */}
      <motion.div
        initial="initial"
        animate={prefersReducedMotion ? "reduced" : "animate"}
        variants={pulseVariants}
        className="absolute inset-0 rounded-full"
        style={{
          background: `radial-gradient(circle, ${accent.glow} 0%, ${accent.glow.replace('0.4', '0.2')} 40%, transparent 70%)`,
          filter: 'blur(20px)',
          willChange: 'transform, opacity'
        }}
      />
      
      {/* Secondary Glow Ring */}
      <motion.div
        initial="initial"
        animate={prefersReducedMotion ? "reduced" : "animate"}
        variants={{
          ...pulseVariants,
          animate: {
            ...pulseVariants.animate,
            transition: {
              ...pulseVariants.animate.transition,
              delay: 0.5,
              duration: 4
            }
          }
        }}
        className="absolute rounded-full"
        style={{
          top: '20%',
          left: '20%',
          right: '20%',
          bottom: '20%',
          background: `radial-gradient(circle, ${accent.secondary}40 0%, transparent 60%)`,
          filter: 'blur(15px)',
          willChange: 'transform, opacity'
        }}
      />

      {/* Inner Core Glow */}
      <motion.div
        initial={{ scale: 0.5, opacity: 0.3 }}
        animate={prefersReducedMotion ? { scale: 1, opacity: 0.5 } : {
          scale: [0.5, 0.8, 0.6, 0.7, 0.5],
          opacity: [0.3, 0.9, 0.4, 0.7, 0.3],
        }}
        transition={{
          duration: 2.5,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 1
        }}
        className="absolute rounded-full"
        style={{
          top: '35%',
          left: '35%',
          right: '35%',
          bottom: '35%',
          background: `linear-gradient(135deg, ${accent.primary}, ${accent.secondary})`,
          filter: 'blur(8px)',
          willChange: 'transform, opacity'
        }}
      />
    </div>
  )
}