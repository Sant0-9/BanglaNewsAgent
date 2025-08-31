"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Newspaper } from "lucide-react"
import { cn } from "../../lib/utils"

export interface FloatingLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  showRipples?: boolean
}

const sizeClasses = {
  sm: 'w-12 h-12',
  md: 'w-16 h-16', 
  lg: 'w-24 h-24',
  xl: 'w-32 h-32'
}

const iconSizes = {
  sm: 'h-6 w-6',
  md: 'h-8 w-8',
  lg: 'h-12 w-12', 
  xl: 'h-16 w-16'
}

export function FloatingLogo({ 
  size = 'xl', 
  className,
  showRipples = true 
}: FloatingLogoProps) {
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

  // Floating animation variants
  const floatingVariants = {
    reduced: {
      y: 0,
      rotate: 0,
      scale: 1
    },
    animate: {
      y: [-8, 8, -8],
      rotate: [-1, 1, -1],
      scale: [1, 1.02, 1],
      transition: {
        duration: 4,
        repeat: Infinity,
        ease: "easeInOut",
        times: [0, 0.5, 1]
      }
    }
  }

  // Water ripple keyframes for CSS animation
  const rippleStyle = showRipples && !prefersReducedMotion ? {
    background: `
      radial-gradient(circle at 30% 70%, rgba(124, 58, 237, 0.15) 0%, transparent 50%),
      radial-gradient(circle at 70% 30%, rgba(6, 182, 212, 0.15) 0%, transparent 50%),
      radial-gradient(circle at 50% 50%, rgba(124, 58, 237, 0.08) 0%, transparent 60%)
    `,
    maskImage: `
      radial-gradient(circle at 50% 50%, black 0%, black 40%, transparent 70%)
    `,
    WebkitMaskImage: `
      radial-gradient(circle at 50% 50%, black 0%, black 40%, transparent 70%)
    `,
    animation: prefersReducedMotion ? 'none' : 'waterRipple 8s ease-in-out infinite'
  } : {}

  return (
    <div className={cn("relative inline-block", className)}>
      {/* Water Ripple Background Effect */}
      {showRipples && (
        <div 
          className="absolute inset-0 -m-8 rounded-full pointer-events-none"
          style={rippleStyle}
        />
      )}
      
      {/* Floating Logo */}
      <motion.div
        className={cn(
          "relative bg-gradient-to-br from-primary via-primary/90 to-accent rounded-3xl shadow-2xl",
          "flex items-center justify-center",
          "backdrop-blur-xl border border-primary/20",
          sizeClasses[size]
        )}
        variants={floatingVariants}
        animate={prefersReducedMotion ? "reduced" : "animate"}
        style={{
          willChange: prefersReducedMotion ? 'auto' : 'transform',
          boxShadow: prefersReducedMotion 
            ? '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
            : '0 25px 50px -12px rgba(124, 58, 237, 0.4), 0 0 0 1px rgba(124, 58, 237, 0.1)'
        }}
      >
        {/* Logo Icon */}
        <Newspaper 
          className={cn(
            "text-primary-foreground drop-shadow-lg",
            iconSizes[size]
          )} 
        />
        
        {/* Subtle Inner Glow */}
        <div 
          className="absolute inset-0 rounded-3xl bg-gradient-to-br from-white/20 to-transparent opacity-50 pointer-events-none"
        />
      </motion.div>

      {/* Global CSS for water ripple animation */}
      <style jsx>{`
        @keyframes waterRipple {
          0%, 100% {
            background-position: 0% 50%, 100% 50%, 50% 0%;
            transform: scale(1) rotate(0deg);
          }
          25% {
            background-position: 25% 75%, 75% 25%, 25% 75%;
            transform: scale(1.05) rotate(0.5deg);
          }
          50% {
            background-position: 100% 50%, 0% 50%, 50% 100%;
            transform: scale(1.02) rotate(-0.5deg);
          }
          75% {
            background-position: 75% 25%, 25% 75%, 75% 25%;
            transform: scale(1.03) rotate(0.3deg);
          }
        }
      `}</style>
    </div>
  )
}