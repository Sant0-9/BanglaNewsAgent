"use client"

import { motion, AnimatePresence } from "framer-motion"
import { useEffect } from "react"
import { cn } from "../../lib/utils"
import { AuraPulse } from "./aura-pulse"
import { ParticleHalo } from "./particle-halo" 
import { ThinkingSteps } from "./thinking-steps"
import { type RouteMode } from "../../lib/loading-accents"

export interface ThinkingOverlayProps {
  isVisible: boolean
  mode?: RouteMode
  className?: string
  onPhaseChange?: (phase: number) => void
}

export function ThinkingOverlay({
  isVisible,
  mode = 'general',
  className,
  onPhaseChange
}: ThinkingOverlayProps) {
  useEffect(() => {
    if (isVisible) {
      // Disable pointer events on body to prevent interaction with chat list
      document.body.style.pointerEvents = 'none'
      // But keep overlay interactive
      const overlay = document.querySelector('[data-thinking-overlay]')
      if (overlay) {
        ;(overlay as HTMLElement).style.pointerEvents = 'auto'
      }
    } else {
      document.body.style.pointerEvents = ''
    }

    return () => {
      document.body.style.pointerEvents = ''
    }
  }, [isVisible])

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          data-thinking-overlay
          initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
          animate={{ 
            opacity: 1, 
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)"
          }}
          exit={{ 
            opacity: 0, 
            backdropFilter: "blur(0px)",
            WebkitBackdropFilter: "blur(0px)"
          }}
          transition={{ 
            duration: 0.3,
            ease: [0.22, 1, 0.36, 1]
          }}
          className={cn(
            "fixed inset-0 z-50 bg-black/20 dark:bg-black/40",
            "flex items-center justify-center",
            "pointer-events-none",
            className
          )}
          style={{
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)"
          }}
          aria-live="polite"
          aria-label="Preparing response"
          role="status"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: -10 }}
            transition={{ 
              duration: 0.4,
              delay: 0.1,
              ease: [0.22, 1, 0.36, 1]
            }}
            className="relative flex items-center justify-center"
          >
            {/* Aura Pulse Background */}
            <AuraPulse mode={mode} />
            
            {/* Particle Halo */}
            <ParticleHalo mode={mode} />
            
            {/* Thinking Steps Content */}
            <div className="relative z-10">
              <ThinkingSteps 
                mode={mode} 
                onPhaseChange={onPhaseChange}
              />
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}