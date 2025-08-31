"use client"

import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { useGraphicsStore } from '../../lib/stores/graphics-store'

// This component runs inside the Canvas and tracks performance
export function CanvasPerformanceMonitor() {
  const frameCount = useRef(0)
  const lastTime = useRef(performance.now())
  const { qualityTier, settings, deviceInfo } = useGraphicsStore()

  useFrame(() => {
    frameCount.current++
    const currentTime = performance.now()
    const deltaTime = currentTime - lastTime.current

    // Update performance data every 2 seconds in development
    if (deltaTime >= 2000 && process.env.NODE_ENV === 'development') {
      const fps = (frameCount.current / deltaTime) * 1000
      const frameTime = deltaTime / frameCount.current

      // Calculate approximate particle count
      const isMobile = deviceInfo.isMobile || (typeof window !== 'undefined' && window.innerWidth < 768)
      let emberCount = 0
      let dustCount = 0
      let textCount = 0

      if (settings.enableParticles) {
        if (isMobile) {
          switch (qualityTier) {
            case 'high': emberCount = 100; dustCount = 75; textCount = 40; break
            case 'medium': emberCount = 75; dustCount = 50; textCount = 25; break
            case 'low': emberCount = 50; dustCount = 30; textCount = 15; break
            case 'battery': emberCount = 25; dustCount = 15; textCount = 8; break
          }
        } else {
          switch (qualityTier) {
            case 'high': emberCount = 1500; dustCount = 1200; textCount = 800; break
            case 'medium': emberCount = 800; dustCount = 600; textCount = 400; break
            case 'low': emberCount = 300; dustCount = 250; textCount = 150; break
            case 'battery': emberCount = 150; dustCount = 100; textCount = 80; break
          }
        }
      }

      // Log performance data in development
      console.log(`🔥 Canvas Performance:`, {
        fps: `${Math.round(fps)} FPS`,
        frameTime: `${Math.round(frameTime * 100) / 100}ms`,
        total: `${emberCount + dustCount + textCount} elements`,
        breakdown: `${emberCount} embers + ${dustCount} dust + ${textCount} Bengali words`,
        tier: qualityTier,
        mobile: isMobile,
        status: fps >= 55 ? '✅ Excellent' : fps >= 45 ? '⚠️ Good' : '❌ Poor'
      })

      frameCount.current = 0
      lastTime.current = currentTime
    }
  })

  // This component doesn't render anything
  return null
}