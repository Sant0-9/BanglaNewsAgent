import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type QualityTier = 'high' | 'medium' | 'low' | 'battery'

export interface GraphicsState {
  qualityTier: QualityTier
  isInitialized: boolean
  deviceInfo: {
    gpu?: string
    tier?: number
    type?: string
    isMobile?: boolean
  }
  settings: {
    enableParticles: boolean
    enablePostProcessing: boolean
    enableShadows: boolean
    pixelRatio: number
    maxFPS: number
  }
}

export interface GraphicsActions {
  setQualityTier: (tier: QualityTier) => void
  setDeviceInfo: (info: Partial<GraphicsState['deviceInfo']>) => void
  initialize: () => Promise<void>
  getOptimalSettings: () => GraphicsState['settings']
}

export type GraphicsStore = GraphicsState & GraphicsActions

// Helper to get device pixel ratio safely
const getDevicePixelRatio = () => {
  if (typeof window !== 'undefined') {
    return window.devicePixelRatio || 1
  }
  return 1
}

// Default settings per quality tier
const QUALITY_SETTINGS: Record<QualityTier, GraphicsState['settings']> = {
  high: {
    enableParticles: true,
    enablePostProcessing: true,
    enableShadows: true,
    pixelRatio: Math.min(getDevicePixelRatio(), 2),
    maxFPS: 60
  },
  medium: {
    enableParticles: true,
    enablePostProcessing: false,
    enableShadows: false,
    pixelRatio: Math.min(getDevicePixelRatio(), 1.5),
    maxFPS: 60
  },
  low: {
    enableParticles: false,
    enablePostProcessing: false,
    enableShadows: false,
    pixelRatio: 1,
    maxFPS: 30
  },
  battery: {
    enableParticles: false,
    enablePostProcessing: false,
    enableShadows: false,
    pixelRatio: 1,
    maxFPS: 24
  }
}

export const useGraphicsStore = create<GraphicsStore>()(
  persist(
    (set, get) => ({
      // State
      qualityTier: 'medium', // Default fallback
      isInitialized: false,
      deviceInfo: {},
      settings: QUALITY_SETTINGS.medium,

      // Actions
      setQualityTier: (tier: QualityTier) => {
        set({ 
          qualityTier: tier,
          settings: QUALITY_SETTINGS[tier]
        })
      },

      setDeviceInfo: (info: Partial<GraphicsState['deviceInfo']>) => {
        set(state => ({
          deviceInfo: { ...state.deviceInfo, ...info }
        }))
      },

      getOptimalSettings: () => {
        const { qualityTier } = get()
        return QUALITY_SETTINGS[qualityTier]
      },

      initialize: async () => {
        if (get().isInitialized) return

        try {
          // Dynamic import to avoid SSR issues
          const { getGPUTier } = await import('detect-gpu')
          
          const gpuTier = await getGPUTier({
            glContext: 'webgl2',
            failIfMajorPerformanceCaveat: false,
            benchmarksURL: '/benchmarks'
          })

          // Update device info
          set(state => ({
            deviceInfo: {
              ...state.deviceInfo,
              gpu: gpuTier.gpu,
              tier: gpuTier.tier,
              type: gpuTier.type,
              isMobile: gpuTier.isMobile
            }
          }))

          // Determine optimal quality tier based on GPU detection
          let optimalTier: QualityTier = 'medium'

          if (gpuTier.tier >= 3) {
            optimalTier = 'high'
          } else if (gpuTier.tier === 2) {
            optimalTier = 'medium'
          } else if (gpuTier.tier === 1) {
            optimalTier = 'low'
          } else {
            optimalTier = 'battery'
          }

          // Check for battery saver mode or reduced performance preferences
          if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2) {
            optimalTier = optimalTier === 'high' ? 'medium' : 'low'
          }

          // Check for reduced motion preference
          const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
          if (prefersReducedMotion) {
            optimalTier = 'battery'
          }

          // Mobile optimization with special handling
          if (gpuTier.isMobile) {
            // More aggressive tier reduction for mobile
            if (optimalTier === 'high') {
              optimalTier = 'low' // Skip medium, go directly to low
            } else if (optimalTier === 'medium') {
              optimalTier = 'battery' // Skip low, go to battery
            } else {
              optimalTier = 'battery'
            }
          }

          set({ 
            qualityTier: optimalTier,
            settings: QUALITY_SETTINGS[optimalTier],
            isInitialized: true
          })

          console.log('Graphics initialized:', {
            tier: optimalTier,
            gpu: gpuTier.gpu,
            gpuTier: gpuTier.tier,
            isMobile: gpuTier.isMobile
          })

        } catch (error) {
          console.warn('GPU detection failed, using fallback settings:', error)
          
          // Fallback: basic mobile detection and conservative settings
          const isMobile = /Mobile|Android|iPhone|iPad/.test(navigator.userAgent)
          const fallbackTier: QualityTier = isMobile ? 'low' : 'medium'
          
          set({
            qualityTier: fallbackTier,
            settings: QUALITY_SETTINGS[fallbackTier],
            deviceInfo: { isMobile },
            isInitialized: true
          })
        }
      }
    }),
    {
      name: 'graphics-settings',
      partialize: (state) => ({ 
        qualityTier: state.qualityTier,
        // Don't persist deviceInfo as it should be detected fresh each session
      }),
    }
  )
)