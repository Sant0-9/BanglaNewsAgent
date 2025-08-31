"use client"

import { useState, useCallback, useEffect, useRef } from 'react'
import { type RouteMode } from '../lib/loading-accents'
import { type ThinkingPhase } from '@/components/loading/thinking-steps'

export type LoadingState = 'idle' | 'thinking' | 'generating' | 'error'

interface LoadingSystemOptions {
  mode?: RouteMode
  onPhaseChange?: (phase: number) => void
  onStateChange?: (state: LoadingState) => void
  longRunningThreshold?: number // milliseconds to show "still working" hint
}

export interface LoadingSystemState {
  state: LoadingState
  isThinkingVisible: boolean
  isGeneratingVisible: boolean
  currentPhase: number
  showLongRunningHint: boolean
  realPhaseEvents: ThinkingPhase[]
  timeElapsed: number
}

export interface LoadingSystemActions {
  startThinking: () => void
  startGenerating: () => void
  stop: () => void
  cancel: () => void
  addPhaseEvent: (phase: ThinkingPhase) => void
  reset: () => void
}

export function useLoadingSystem(options: LoadingSystemOptions = {}) {
  const {
    mode = 'general',
    onPhaseChange,
    onStateChange,
    longRunningThreshold = 15000
  } = options

  const [state, setState] = useState<LoadingState>('idle')
  const [currentPhase, setCurrentPhase] = useState(0)
  const [showLongRunningHint, setShowLongRunningHint] = useState(false)
  const [realPhaseEvents, setRealPhaseEvents] = useState<ThinkingPhase[]>([])
  const [timeElapsed, setTimeElapsed] = useState(0)
  
  const startTimeRef = useRef<number | null>(null)
  const longRunningTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  // Clean up timers
  const clearTimers = useCallback(() => {
    if (longRunningTimeoutRef.current) {
      clearTimeout(longRunningTimeoutRef.current)
      longRunningTimeoutRef.current = null
    }
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  // Start elapsed time counter
  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now()
    setTimeElapsed(0)
    
    timerRef.current = setInterval(() => {
      if (startTimeRef.current) {
        setTimeElapsed(Date.now() - startTimeRef.current)
      }
    }, 100)
  }, [])

  // Stop elapsed time counter
  const stopTimer = useCallback(() => {
    clearTimers()
    startTimeRef.current = null
  }, [clearTimers])

  const startThinking = useCallback(() => {
    setState('thinking')
    setCurrentPhase(0)
    setShowLongRunningHint(false)
    setRealPhaseEvents([])
    
    startTimer()
    onStateChange?.('thinking')
    
    // Set up long running hint
    longRunningTimeoutRef.current = setTimeout(() => {
      setShowLongRunningHint(true)
    }, longRunningThreshold)
  }, [onStateChange, longRunningThreshold, startTimer])

  const startGenerating = useCallback(() => {
    setState('generating')
    setShowLongRunningHint(false)
    onStateChange?.('generating')
  }, [onStateChange])

  const stop = useCallback(() => {
    setState('idle')
    setCurrentPhase(0)
    setShowLongRunningHint(false)
    setRealPhaseEvents([])
    stopTimer()
    onStateChange?.('idle')
  }, [onStateChange, stopTimer])

  const cancel = useCallback(() => {
    setState('idle')
    setCurrentPhase(0)
    setShowLongRunningHint(false)
    setRealPhaseEvents([])
    stopTimer()
    onStateChange?.('idle')
  }, [onStateChange, stopTimer])

  const addPhaseEvent = useCallback((phase: ThinkingPhase) => {
    setRealPhaseEvents(prev => {
      const newEvents = [...prev, phase]
      // Keep only the last 4 events to prevent memory leak
      return newEvents.slice(-4)
    })
  }, [])

  const reset = useCallback(() => {
    setState('idle')
    setCurrentPhase(0)
    setShowLongRunningHint(false)
    setRealPhaseEvents([])
    setTimeElapsed(0)
    stopTimer()
  }, [stopTimer])

  // Handle phase changes
  const handlePhaseChange = useCallback((phase: number) => {
    setCurrentPhase(phase)
    onPhaseChange?.(phase)
  }, [onPhaseChange])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimers()
    }
  }, [clearTimers])

  // Derived state
  const loadingState: LoadingSystemState = {
    state,
    isThinkingVisible: state === 'thinking',
    isGeneratingVisible: state === 'generating',
    currentPhase,
    showLongRunningHint,
    realPhaseEvents,
    timeElapsed
  }

  const actions: LoadingSystemActions = {
    startThinking,
    startGenerating,
    stop,
    cancel,
    addPhaseEvent,
    reset
  }

  return {
    ...loadingState,
    actions,
    mode,
    onPhaseChange: handlePhaseChange
  }
}