"use client"

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'

// Dynamically import HeroCanvas with no SSR
const HeroCanvas = dynamic(() => import('./hero-canvas').then(mod => ({ default: mod.HeroCanvas })), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-fire-ember border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-muted-foreground animate-pulse">Loading 3D canvas...</p>
      </div>
    </div>
  )
})

interface LazyHeroCanvasProps {
  mousePosition?: { x: number; y: number }
  className?: string
}

export function LazyHeroCanvas({ mousePosition, className }: LazyHeroCanvasProps) {
  const [shouldLoad, setShouldLoad] = useState(false)

  useEffect(() => {
    // Delay canvas loading to ensure the shell is rendered first
    const timer = setTimeout(() => {
      setShouldLoad(true)
    }, 100) // Small delay to ensure DOM is ready

    return () => clearTimeout(timer)
  }, [])

  if (!shouldLoad) {
    return (
      <div className="absolute inset-0 flex items-center justify-center opacity-50">
        <div className="flex flex-col items-center gap-2">
          <div className="w-6 h-6 border border-fire-ember border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-muted-foreground">Initializing...</p>
        </div>
      </div>
    )
  }

  return (
    <HeroCanvas 
      mousePosition={mousePosition} 
      className={className}
    />
  )
}