"use client"

import { motion } from "framer-motion"
import { useEffect, useState } from "react"
import { routeAccent, type RouteMode } from "../../lib/loading-accents"
import { cn } from "../../lib/utils"

export interface ParticleHaloProps {
  mode?: RouteMode
  className?: string
  particleCount?: number
}

export function ParticleHalo({ 
  mode = 'general', 
  className,
  particleCount = 24 
}: ParticleHaloProps) {
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

  // Generate particles in circular formation
  const particles = Array.from({ length: particleCount }, (_, i) => {
    const angle = (360 / particleCount) * i
    const radius = 120 + (i % 3) * 15 // Slight variation in radius for parallax
    const size = 3 + (i % 3) // Varying sizes: 3px, 4px, 5px
    const opacity = 0.4 + (i % 3) * 0.2 // Varying opacity: 0.4, 0.6, 0.8
    
    return {
      id: i,
      angle,
      radius,
      size,
      opacity,
      delay: (i * 0.1) % 2 // Stagger animation delays
    }
  })

  if (prefersReducedMotion) {
    // Static dots for reduced motion
    return (
      <div 
        className={cn("absolute pointer-events-none", className)}
        style={{
          width: '300px',
          height: '300px',
          transform: 'translate(-50%, -50%)',
          top: '50%',
          left: '50%'
        }}
      >
        {particles.map((particle) => {
          const x = Math.cos((particle.angle * Math.PI) / 180) * particle.radius
          const y = Math.sin((particle.angle * Math.PI) / 180) * particle.radius
          
          return (
            <div
              key={particle.id}
              className="absolute rounded-full"
              style={{
                left: `calc(50% + ${x}px)`,
                top: `calc(50% + ${y}px)`,
                width: `${particle.size}px`,
                height: `${particle.size}px`,
                backgroundColor: accent.particle,
                opacity: particle.opacity * 0.6,
                transform: 'translate(-50%, -50%)'
              }}
            />
          )
        })}
      </div>
    )
  }

  return (
    <div 
      className={cn("absolute pointer-events-none", className)}
      style={{
        width: '300px',
        height: '300px',
        transform: 'translate(-50%, -50%)',
        top: '50%',
        left: '50%'
      }}
    >
      {/* Rotating container for orbital motion */}
      <motion.div
        className="absolute inset-0"
        animate={{ rotate: 360 }}
        transition={{
          duration: 20,
          repeat: Infinity,
          ease: "linear"
        }}
        style={{ willChange: 'transform' }}
      >
        {particles.map((particle) => {
          const x = Math.cos((particle.angle * Math.PI) / 180) * particle.radius
          const y = Math.sin((particle.angle * Math.PI) / 180) * particle.radius
          
          return (
            <motion.div
              key={particle.id}
              className="absolute rounded-full"
              style={{
                left: `calc(50% + ${x}px)`,
                top: `calc(50% + ${y}px)`,
                width: `${particle.size}px`,
                height: `${particle.size}px`,
                backgroundColor: accent.particle,
                willChange: 'transform, opacity'
              }}
              initial={{ 
                opacity: 0, 
                scale: 0,
                transform: 'translate(-50%, -50%)'
              }}
              animate={{ 
                opacity: [0, particle.opacity, particle.opacity * 0.5, particle.opacity],
                scale: [0, 1, 1.2, 1],
                transform: 'translate(-50%, -50%)'
              }}
              transition={{
                duration: 2 + particle.delay,
                repeat: Infinity,
                ease: "easeInOut",
                delay: particle.delay
              }}
            />
          )
        })}
      </motion.div>

      {/* Counter-rotating inner ring for parallax effect */}
      <motion.div
        className="absolute inset-0"
        animate={{ rotate: -360 }}
        transition={{
          duration: 15,
          repeat: Infinity,
          ease: "linear"
        }}
        style={{ willChange: 'transform' }}
      >
        {particles.slice(0, 12).map((particle, i) => {
          const angle = (360 / 12) * i
          const x = Math.cos((angle * Math.PI) / 180) * 80
          const y = Math.sin((angle * Math.PI) / 180) * 80
          
          return (
            <motion.div
              key={`inner-${i}`}
              className="absolute rounded-full"
              style={{
                left: `calc(50% + ${x}px)`,
                top: `calc(50% + ${y}px)`,
                width: '2px',
                height: '2px',
                backgroundColor: accent.primary,
                willChange: 'transform, opacity'
              }}
              initial={{ 
                opacity: 0,
                transform: 'translate(-50%, -50%)'
              }}
              animate={{ 
                opacity: [0, 0.8, 0.3, 0.6],
                transform: 'translate(-50%, -50%)'
              }}
              transition={{
                duration: 3,
                repeat: Infinity,
                ease: "easeInOut",
                delay: i * 0.2
              }}
            />
          )
        })}
      </motion.div>
    </div>
  )
}