"use client"

import { motion, AnimatePresence } from "framer-motion"
import { useEffect, useState } from "react"
import { Progress } from "../ui/progress"
import { routeAccent, type RouteMode } from "../../lib/loading-accents"
import { cn } from "../../lib/utils"
import { 
  Search, 
  Layers, 
  ArrowUpDown, 
  MessageSquare,
  CheckCircle2
} from "lucide-react"

export type ThinkingPhase = 'fetching' | 'deduping' | 'reranking' | 'summarizing'

export interface ThinkingStep {
  id: ThinkingPhase
  label: string
  bengaliLabel: string
  icon: React.ReactNode
  duration: number
}

const THINKING_STEPS: ThinkingStep[] = [
  {
    id: 'fetching',
    label: 'Fetching sources…',
    bengaliLabel: 'তথ্যসূত্র সংগ্রহ করছি…',
    icon: <Search className="h-4 w-4" />,
    duration: 800
  },
  {
    id: 'deduping',
    label: 'Deduping & clustering…',
    bengaliLabel: 'ডেটা বিশ্লেষণ করছি…',
    icon: <Layers className="h-4 w-4" />,
    duration: 600
  },
  {
    id: 'reranking',
    label: 'Reranking evidence…',
    bengaliLabel: 'তথ্য সাজাচ্ছি…',
    icon: <ArrowUpDown className="h-4 w-4" />,
    duration: 700
  },
  {
    id: 'summarizing',
    label: 'Summarizing in Bangla…',
    bengaliLabel: 'বাংলায় সারসংক্ষেপ তৈরি করছি…',
    icon: <MessageSquare className="h-4 w-4" />,
    duration: 500
  }
]

export interface ThinkingStepsProps {
  mode?: RouteMode
  className?: string
  onPhaseChange?: (phase: number) => void
  realPhaseEvents?: ThinkingPhase[]
  useRealEvents?: boolean
}

export function ThinkingSteps({ 
  mode = 'general', 
  className,
  onPhaseChange,
  realPhaseEvents = [],
  useRealEvents = false
}: ThinkingStepsProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [progress, setProgress] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set())
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

  useEffect(() => {
    if (useRealEvents && realPhaseEvents.length > 0) {
      // Use real phase events when available
      const latestPhaseIndex = THINKING_STEPS.findIndex(
        step => step.id === realPhaseEvents[realPhaseEvents.length - 1]
      )
      if (latestPhaseIndex !== -1) {
        setCurrentStep(latestPhaseIndex)
        setProgress(((latestPhaseIndex + 1) / THINKING_STEPS.length) * 100)
        
        const newCompleted = new Set<number>()
        for (let i = 0; i <= latestPhaseIndex; i++) {
          newCompleted.add(i)
        }
        setCompletedSteps(newCompleted)
        onPhaseChange?.(latestPhaseIndex)
      }
      return
    }

    // Auto-advance through phases
    let timeouts: NodeJS.Timeout[] = []
    let totalElapsed = 0
    
    THINKING_STEPS.forEach((step, index) => {
      const timeout = setTimeout(() => {
        setCurrentStep(index)
        setProgress(((index + 1) / THINKING_STEPS.length) * 100)
        
        setCompletedSteps(prev => new Set([...prev, index]))
        onPhaseChange?.(index)
        
        // Animate progress within this step
        if (index < THINKING_STEPS.length - 1) {
          const progressTimeout = setTimeout(() => {
            setProgress(((index + 1.5) / THINKING_STEPS.length) * 100)
          }, step.duration * 0.7)
          timeouts.push(progressTimeout)
        }
      }, totalElapsed)
      
      timeouts.push(timeout)
      totalElapsed += step.duration
    })

    return () => {
      timeouts.forEach(clearTimeout)
    }
  }, [useRealEvents, realPhaseEvents, onPhaseChange])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      transition={{ 
        duration: 0.4, 
        ease: [0.22, 1, 0.36, 1],
        delay: 0.2 
      }}
      className={cn(
        "bg-card/90 backdrop-blur-xl border border-border/50 rounded-2xl p-6 shadow-2xl",
        "min-w-[320px] max-w-[400px]",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <motion.div
          className="w-8 h-8 rounded-xl flex items-center justify-center"
          style={{ 
            background: `linear-gradient(135deg, ${accent.primary}, ${accent.secondary})` 
          }}
          animate={prefersReducedMotion ? {} : {
            scale: [1, 1.1, 1],
            rotate: [0, 5, -5, 0]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <MessageSquare className="h-4 w-4 text-white" />
        </motion.div>
        <div>
          <h3 className="font-semibold text-foreground">AI Processing</h3>
          <p className="text-sm text-muted-foreground">প্রক্রিয়াকরণ চলছে</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-muted-foreground">Progress</span>
          <span className="text-sm font-medium text-foreground">
            {Math.round(progress)}%
          </span>
        </div>
        <Progress 
          value={progress} 
          className="h-2"
          style={{
            '--progress-foreground': prefersReducedMotion 
              ? accent.primary 
              : `linear-gradient(90deg, ${accent.primary}, ${accent.secondary})`
          }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {THINKING_STEPS.map((step, index) => {
          const isActive = currentStep === index
          const isCompleted = completedSteps.has(index)
          const isPending = index > currentStep
          
          return (
            <motion.div
              key={step.id}
              layout
              className={cn(
                "flex items-center gap-3 p-3 rounded-xl transition-all duration-300",
                isActive && "bg-accent/10 scale-105",
                isCompleted && "bg-accent/5",
                isPending && "opacity-40"
              )}
            >
              <motion.div
                className={cn(
                  "flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center transition-all duration-300",
                  isCompleted && "bg-green-500",
                  isActive && "bg-primary",
                  isPending && "bg-muted border border-border"
                )}
                animate={isActive && !prefersReducedMotion ? {
                  scale: [1, 1.1, 1],
                  background: [`${accent.primary}`, `${accent.secondary}`, `${accent.primary}`]
                } : {}}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <AnimatePresence mode="wait">
                  {isCompleted ? (
                    <motion.div
                      key="check"
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <CheckCircle2 className="h-3 w-3 text-white" />
                    </motion.div>
                  ) : (
                    <motion.div
                      key="icon"
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0, opacity: 0 }}
                      className={cn(
                        isActive ? "text-primary-foreground" : "text-muted-foreground"
                      )}
                    >
                      {step.icon}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
              
              <div className="flex-1 min-w-0">
                <motion.div
                  layout
                  className={cn(
                    "font-medium transition-colors duration-300",
                    isActive && "text-foreground",
                    isCompleted && "text-muted-foreground",
                    isPending && "text-muted-foreground"
                  )}
                >
                  {step.bengaliLabel}
                </motion.div>
                <motion.div 
                  layout
                  className="text-xs text-muted-foreground mt-0.5"
                >
                  {step.label}
                </motion.div>
              </div>
              
              {isActive && !prefersReducedMotion && (
                <motion.div
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ 
                    opacity: [0, 1, 0],
                    scale: [0, 1, 0],
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: accent.primary }}
                />
              )}
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}