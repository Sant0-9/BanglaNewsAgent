"use client"

import { Suspense, useEffect, useRef, useState, useCallback, memo } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { ACESFilmicToneMapping, SRGBColorSpace, PerspectiveCamera } from 'three'
import { useGraphicsStore } from '../../lib/stores/graphics-store'
import { EmberParticles, DustParticles, BanglaWordField } from './particles'
import { CanvasPerformanceMonitor } from './canvas-performance-monitor'
import Stats from 'stats.js'

// FPS Counter component (dev only)
function FPSCounter() {
  const statsRef = useRef<Stats | null>(null)
  const mountRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return

    const stats = new Stats()
    stats.showPanel(0) // 0: fps, 1: ms, 2: mb
    stats.dom.style.position = 'absolute'
    stats.dom.style.left = '0px'
    stats.dom.style.top = '0px'
    stats.dom.style.zIndex = '1000'
    
    if (mountRef.current) {
      mountRef.current.appendChild(stats.dom)
    }
    
    statsRef.current = stats

    const animate = () => {
      stats.begin()
      stats.end()
      requestAnimationFrame(animate)
    }
    animate()

    return () => {
      if (mountRef.current && stats.dom) {
        mountRef.current.removeChild(stats.dom)
      }
    }
  }, [])

  if (process.env.NODE_ENV !== 'development') return null

  return <div ref={mountRef} className="absolute top-0 left-0 z-[1000] pointer-events-none" />
}

// Scene setup component
const Scene = memo(function Scene() {
  const { camera, gl } = useThree()
  const { settings } = useGraphicsStore()

  useEffect(() => {
    // Configure camera
    if (camera instanceof PerspectiveCamera) {
      camera.fov = 75
      camera.near = 0.1
      camera.far = 1000
      camera.position.set(0, 0, 5)
      camera.updateProjectionMatrix()
    }

    // Configure renderer
    gl.setPixelRatio(settings.pixelRatio)
    gl.toneMapping = ACESFilmicToneMapping
    gl.toneMappingExposure = 1.0
    gl.outputColorSpace = SRGBColorSpace
    gl.setClearColor('#0a0a0b', 1) // Charcoal-950 background

    // Enable shadows if supported by quality tier
    gl.shadowMap.enabled = settings.enableShadows
    if (settings.enableShadows) {
      gl.shadowMap.type = 2 // PCFSoftShadowMap
    }

    console.log('Three.js renderer configured:', {
      pixelRatio: settings.pixelRatio,
      shadows: settings.enableShadows,
      toneMapping: 'ACES Filmic',
      colorSpace: 'sRGB'
    })
  }, [camera, gl, settings])

  return null
})

// Warm lighting setup
const WarmLights = memo(function WarmLights() {
  const { settings } = useGraphicsStore()
  
  return (
    <>
      {/* Ambient light with warm temperature */}
      <ambientLight 
        intensity={0.3} 
        color="#ffa366" // Warm amber tone (~2700K)
      />
      
      {/* Key light - warm and directional */}
      <directionalLight
        position={[10, 10, 5]}
        intensity={0.8}
        color="#ffcc80" // Warm gold tone (~3000K)
        castShadow={settings.enableShadows}
        shadow-mapSize-width={settings.enableShadows ? 2048 : 512}
        shadow-mapSize-height={settings.enableShadows ? 2048 : 512}
        shadow-camera-near={0.5}
        shadow-camera-far={50}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
      />
      
      {/* Fill light - cooler but still warm */}
      <directionalLight
        position={[-5, 5, 8]}
        intensity={0.4}
        color="#ffb366" // Slightly cooler warm tone (~3200K)
      />
      
      {/* Rim light for subtle fire glow */}
      <pointLight
        position={[0, -5, -10]}
        intensity={0.6}
        color="#ff8a65" // Fire ember color
        distance={20}
        decay={2}
      />
      
      {/* Subtle accent lights matching fire theme */}
      <pointLight
        position={[15, 0, 0]}
        intensity={0.2}
        color="#ff7043" // Fire molten color
        distance={25}
        decay={2}
      />
      
      <pointLight
        position={[-15, 0, 0]}
        intensity={0.2}
        color="#ffab40" // Fire amber color
        distance={25}
        decay={2}
      />
    </>
  )
})

// Test geometry to validate Three.js is working
const TestGeometry = memo(function TestGeometry() {
  const meshRef = useRef<any>(null)

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime) * 0.1
      meshRef.current.rotation.y += 0.01
    }
  })

  return (
    <mesh ref={meshRef} position={[0, 0, 0]}>
      <sphereGeometry args={[0.5, 32, 32]} />
      <meshStandardMaterial 
        color="#ff7a1a" 
        transparent 
        opacity={0.3}
        roughness={0.2}
        metalness={0.8}
      />
    </mesh>
  )
})

// Camera controller for subtle parallax
function CameraController({ mousePosition }: { mousePosition: { x: number; y: number } }) {
  const { camera } = useThree()
  const { settings } = useGraphicsStore()

  useFrame(() => {
    if (camera && settings.pixelRatio > 1) {
      // Subtle camera movement based on mouse position
      const targetX = mousePosition.x * 0.5
      const targetY = mousePosition.y * 0.3
      
      camera.position.x += (targetX - camera.position.x) * 0.05
      camera.position.y += (targetY - camera.position.y) * 0.05
      camera.lookAt(0, 0, 0)
    }
  })

  return null
}

// Loading fallback
function CanvasLoader() {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-fire-ember border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

// Main HeroCanvas component
interface HeroCanvasProps {
  mousePosition?: { x: number; y: number }
  className?: string
}

export function HeroCanvas({ mousePosition = { x: 0, y: 0 }, className }: HeroCanvasProps) {
  const [isMounted, setIsMounted] = useState(false)
  const { initialize, isInitialized, settings, qualityTier } = useGraphicsStore()

  useEffect(() => {
    // Initialize graphics detection
    if (!isInitialized) {
      initialize()
    }
    setIsMounted(true)
  }, [initialize, isInitialized])

  if (!isMounted) {
    return <CanvasLoader />
  }

  return (
    <>
      <FPSCounter />
      <Canvas
        className={className}
        dpr={settings.pixelRatio}
        performance={{ min: 0.5 }}
        gl={{
          alpha: true,
          antialias: settings.pixelRatio > 1,
          powerPreference: settings.qualityTier === 'battery' ? 'low-power' : 'high-performance',
          preserveDrawingBuffer: false,
          failIfMajorPerformanceCaveat: false,
        }}
        camera={{
          fov: 75,
          near: 0.1,
          far: 1000,
          position: [0, 0, 5]
        }}
        frameloop="always"
        resize={{ scroll: false }}
      >
        <Suspense fallback={null}>
          <Scene />
          <WarmLights />
          <CameraController mousePosition={mousePosition} />
          <CanvasPerformanceMonitor />
          
          {/* Particle Systems */}
          {settings.enableParticles && (
            <group>
              {/* Dust particles - rendered first (background layer) */}
              <DustParticles />
              
              {/* Bengali word field - middle layer with depth sorting */}
              <BanglaWordField />
              
              {/* Ember particles - rendered on top with additive blending */}
              <EmberParticles />
            </group>
          )}
          
          {/* Test geometry - disabled in production */}
          {process.env.NODE_ENV === 'development' && (
            <TestGeometry />
          )}
        </Suspense>
      </Canvas>
    </>
  )
}