"use client"

import { useState, useCallback, useEffect, useRef } from 'react'
import type { Source } from '../lib/types'

export interface CitationSystemOptions {
  sources: Source[]
  messageId?: string
  enableKeyboardNavigation?: boolean
  highlightDuration?: number
}

export function useCitationSystem({
  sources,
  messageId,
  enableKeyboardNavigation = true,
  highlightDuration = 2000
}: CitationSystemOptions) {
  const [highlightedSources, setHighlightedSources] = useState<Set<number>>(new Set())
  const [highlightedMarkers, setHighlightedMarkers] = useState<Set<number>>(new Set())
  const [currentMarkerIndex, setCurrentMarkerIndex] = useState<number>(-1)
  
  const highlightTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const containerRef = useRef<HTMLElement | null>(null)
  
  // Clear highlight timeout on unmount
  useEffect(() => {
    return () => {
      if (highlightTimeoutRef.current) {
        clearTimeout(highlightTimeoutRef.current)
      }
    }
  }, [])

  // Highlight source and marker
  const highlightItem = useCallback((index: number) => {
    setHighlightedSources(new Set([index]))
    setHighlightedMarkers(new Set([index]))
    
    // Clear previous timeout
    if (highlightTimeoutRef.current) {
      clearTimeout(highlightTimeoutRef.current)
    }
    
    // Auto-clear highlight after duration
    highlightTimeoutRef.current = setTimeout(() => {
      setHighlightedSources(new Set())
      setHighlightedMarkers(new Set())
    }, highlightDuration)
  }, [highlightDuration])

  // Scroll to source in tray and highlight
  const scrollToSource = useCallback((sourceIndex: number) => {
    const sourceElement = document.querySelector(
      `[data-source-index="${sourceIndex}"]`
    )
    
    if (sourceElement) {
      sourceElement.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      })
      highlightItem(sourceIndex)
    }
  }, [highlightItem])

  // Scroll to marker and highlight
  const scrollToMarker = useCallback((markerIndex: number) => {
    const markerElement = document.querySelector(
      `[data-marker-number="${markerIndex + 1}"]`
    )
    
    if (markerElement) {
      markerElement.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      })
      highlightItem(markerIndex)
    }
  }, [highlightItem])

  // Handle marker click
  const handleMarkerClick = useCallback((markerIndex: number) => {
    scrollToSource(markerIndex)
    setCurrentMarkerIndex(markerIndex)
  }, [scrollToSource])

  // Handle source click
  const handleSourceClick = useCallback((sourceIndex: number) => {
    scrollToMarker(sourceIndex)
    setCurrentMarkerIndex(sourceIndex)
  }, [scrollToMarker])

  // Navigate to next/previous marker
  const navigateMarkers = useCallback((direction: 'next' | 'prev') => {
    if (sources.length === 0) return

    let newIndex: number
    
    if (direction === 'next') {
      newIndex = currentMarkerIndex >= sources.length - 1 ? 0 : currentMarkerIndex + 1
    } else {
      newIndex = currentMarkerIndex <= 0 ? sources.length - 1 : currentMarkerIndex - 1
    }
    
    setCurrentMarkerIndex(newIndex)
    scrollToMarker(newIndex)
  }, [sources.length, currentMarkerIndex, scrollToMarker])

  // Keyboard navigation
  useEffect(() => {
    if (!enableKeyboardNavigation || sources.length === 0) return

    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle keys when the message container or its children are focused
      const target = event.target as HTMLElement
      const messageContainer = containerRef.current
      
      if (!messageContainer || !messageContainer.contains(target)) {
        return
      }

      switch (event.key) {
        case ']':
          event.preventDefault()
          navigateMarkers('next')
          break
        case '[':
          event.preventDefault()
          navigateMarkers('prev')
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [enableKeyboardNavigation, sources.length, navigateMarkers])

  // Clear highlights manually
  const clearHighlights = useCallback(() => {
    setHighlightedSources(new Set())
    setHighlightedMarkers(new Set())
    setCurrentMarkerIndex(-1)
    
    if (highlightTimeoutRef.current) {
      clearTimeout(highlightTimeoutRef.current)
      highlightTimeoutRef.current = null
    }
  }, [])

  return {
    // State
    highlightedSources,
    highlightedMarkers,
    currentMarkerIndex,
    containerRef,
    
    // Actions
    handleMarkerClick,
    handleSourceClick,
    scrollToSource,
    scrollToMarker,
    navigateMarkers,
    clearHighlights,
    
    // Utils
    totalSources: sources.length,
    hasKeyboardNavigation: enableKeyboardNavigation && sources.length > 0
  }
}