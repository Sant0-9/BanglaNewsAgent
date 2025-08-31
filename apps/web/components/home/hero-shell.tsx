"use client"

import { useEffect, useRef, useState } from "react"
import { motion } from "framer-motion"
import { cn } from "../../lib/utils"
import { LazyHeroCanvas } from "./lazy-hero-canvas"

interface HeroShellProps {
  children: React.ReactNode
  className?: string
}

interface MousePosition {
  x: number
  y: number
}

export function HeroShell({ children, className }: HeroShellProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const frameRef = useRef<HTMLDivElement>(null)
  const [mousePosition, setMousePosition] = useState<MousePosition>({ x: 0, y: 0 })
  const [isHovered, setIsHovered] = useState(false)
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    // Check for reduced motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReducedMotion(mediaQuery.matches)
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches)
    }
    
    mediaQuery.addEventListener('change', handleChange)

    // Check if mobile device
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768 || 'ontouchstart' in window)
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    
    return () => {
      mediaQuery.removeEventListener('change', handleChange)
      window.removeEventListener('resize', checkMobile)
    }
  }, [])

  useEffect(() => {
    if (!containerRef.current || prefersReducedMotion || isMobile) return

    const handleMouseMove = (e: MouseEvent) => {
      const container = containerRef.current
      if (!container) return

      const rect = container.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      
      // Calculate relative position from center (-1 to 1)
      const relativeX = (e.clientX - centerX) / (rect.width / 2)
      const relativeY = (e.clientY - centerY) / (rect.height / 2)
      
      // Limit the range and smooth the values
      const limitedX = Math.max(-1, Math.min(1, relativeX)) * 0.5
      const limitedY = Math.max(-1, Math.min(1, relativeY)) * 0.5
      
      setMousePosition({ x: limitedX, y: limitedY })
    }

    const handleMouseEnter = () => setIsHovered(true)
    const handleMouseLeave = () => {
      setIsHovered(false)
      setMousePosition({ x: 0, y: 0 })
    }

    const container = containerRef.current
    container.addEventListener('mousemove', handleMouseMove)
    container.addEventListener('mouseenter', handleMouseEnter)
    container.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      container.removeEventListener('mousemove', handleMouseMove)
      container.removeEventListener('mouseenter', handleMouseEnter)
      container.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [prefersReducedMotion, isMobile])

  // Calculate transform values with refined limits for better physicality
  const tiltX = mousePosition.y * 6 // Max 6 degrees (reduced for subtlety)
  const tiltY = mousePosition.x * -6 // Max 6 degrees (inverted, reduced)
  const translateX = mousePosition.x * 3 // Max 3px (subtle movement)
  const translateY = mousePosition.y * 3 // Max 3px

  const shouldAnimate = !prefersReducedMotion && !isMobile

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

      {/* Main Container */}
      <div 
        ref={containerRef}
        className={cn(
          "relative z-10 flex flex-col items-center justify-center min-h-screen px-6 py-16",
          className
        )}
        style={{ perspective: '1000px' }}
      >
        {/* Glass Window Frame */}
        <motion.div
          ref={frameRef}
          className="relative w-full max-w-6xl mx-auto"
          animate={shouldAnimate ? {
            rotateX: tiltX,
            rotateY: tiltY,
            x: translateX,
            y: translateY,
          } : {}}
          transition={{
            type: "spring",
            stiffness: 400,
            damping: 40,
            mass: 0.8,
            restDelta: 0.0001
          }}
        >
          {/* Glass Frame */}
          <div 
            className={cn(
              "relative rounded-3xl overflow-hidden",
              // Glass morphism effects with enhanced depth
              "backdrop-blur-xl bg-gradient-to-br from-charcoal-900/30 via-charcoal-800/20 to-charcoal-700/15",
              // Refined border with subtle gradient
              "border border-fire-gold/10",
              "shadow-2xl shadow-charcoal-950/60"
            )}
            style={{
              boxShadow: shouldAnimate && isHovered
                ? `
                  0 35px 60px -15px rgba(10, 10, 11, 0.7),
                  0 15px 25px -5px rgba(255, 77, 0, 0.15),
                  0 8px 16px -8px rgba(255, 184, 0, 0.1),
                  inset 0 1px 0 0 rgba(255, 255, 255, 0.08),
                  inset 0 -1px 0 0 rgba(255, 77, 0, 0.05),
                  inset 0 0 0 1px rgba(255, 184, 0, 0.05)
                `
                : `
                  0 25px 50px -12px rgba(10, 10, 11, 0.5),
                  0 8px 16px -8px rgba(255, 77, 0, 0.05),
                  inset 0 1px 0 0 rgba(255, 255, 255, 0.04),
                  inset 0 -1px 0 0 rgba(0, 0, 0, 0.08),
                  inset 0 0 0 1px rgba(255, 184, 0, 0.03)
                `
            }}
          >
            {/* Multiple layered frame effects for depth */}
            {/* Outer highlight rim */}
            <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-fire-gold/8 via-transparent to-fire-ember/6 pointer-events-none" />
            
            {/* Inner glass reflection */}
            <div className="absolute inset-[2px] rounded-3xl bg-gradient-to-tr from-fire-gold/5 via-transparent via-transparent to-fire-amber/5 pointer-events-none" />
            
            {/* Surface texture overlay with subtle animation */}
            <motion.div 
              className="absolute inset-0 rounded-3xl pointer-events-none opacity-20"
              animate={shouldAnimate ? {
                background: [
                  `radial-gradient(circle at 30% 20%, rgba(255, 184, 0, 0.1) 0%, transparent 40%),
                   radial-gradient(circle at 70% 80%, rgba(255, 122, 26, 0.1) 0%, transparent 40%),
                   linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, transparent 50%)`,
                  `radial-gradient(circle at 35% 25%, rgba(255, 184, 0, 0.08) 0%, transparent 45%),
                   radial-gradient(circle at 65% 75%, rgba(255, 122, 26, 0.08) 0%, transparent 45%),
                   linear-gradient(135deg, rgba(255, 255, 255, 0.025) 0%, transparent 55%)`,
                  `radial-gradient(circle at 30% 20%, rgba(255, 184, 0, 0.1) 0%, transparent 40%),
                   radial-gradient(circle at 70% 80%, rgba(255, 122, 26, 0.1) 0%, transparent 40%),
                   linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, transparent 50%)`
                ]
              } : {}}
              transition={{
                duration: 8,
                repeat: Infinity,
                ease: "linear"
              }}
            />
            
            {/* Inner shadow for depth */}
            <div 
              className="absolute inset-0 rounded-3xl pointer-events-none"
              style={{
                boxShadow: 'inset 0 4px 12px rgba(0, 0, 0, 0.15), inset 0 -2px 8px rgba(0, 0, 0, 0.1)'
              }}
            />
            
            {/* WebGL Canvas Background */}
            <div className="absolute inset-[2px] rounded-3xl overflow-hidden">
              <LazyHeroCanvas 
                mousePosition={mousePosition}
                className="absolute inset-0 w-full h-full opacity-40"
              />
            </div>
            
            {/* Content Container */}
            <div className="relative z-20 p-8 md:p-12 lg:p-16 bg-gradient-to-br from-charcoal-950/60 via-charcoal-950/40 to-charcoal-950/60 backdrop-blur-sm rounded-3xl">
              {children}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}