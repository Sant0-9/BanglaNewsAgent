"use client"

import React, { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Text } from '@react-three/drei'
import { 
  Group,
  Vector3
} from 'three'
import { useGraphicsStore } from '../../../lib/stores/graphics-store'
import { getBalancedWords, BengaliWord } from '../../../lib/bengali-words'

interface BanglaWordFieldProps {
  count?: number
}

interface WordInstance {
  word: BengaliWord
  position: Vector3
  scale: number
  phase: number
  yawSpeed: number
  glowChance: number
  layer: 'near' | 'mid' | 'far'
  opacity: number
}

export function BanglaWordField({ count: propCount }: BanglaWordFieldProps) {
  const groupRef = useRef<Group>(null)
  const { settings, qualityTier } = useGraphicsStore()

  // Determine word count based on quality tier and mobile detection
  const wordCount = useMemo(() => {
    if (propCount) return propCount
    
    // Check for mobile device
    const isMobile = typeof window !== 'undefined' && (
      /Mobile|Android|iPhone|iPad/.test(navigator.userAgent) ||
      window.innerWidth < 768
    )
    
    if (isMobile) {
      // Mobile-specific counts (much lower for text rendering)
      switch (qualityTier) {
        case 'high': return 40
        case 'medium': return 25
        case 'low': return 15
        case 'battery': return 8
        default: return 20
      }
    }
    
    // Desktop counts
    switch (qualityTier) {
      case 'high': return 800
      case 'medium': return 400
      case 'low': return 150
      case 'battery': return 80
      default: return 400
    }
  }, [qualityTier, propCount])

  // Generate word instances with balanced distribution
  const wordInstances = useMemo(() => {
    const words = getBalancedWords(wordCount)
    const instances: WordInstance[] = []

    for (let i = 0; i < wordCount; i++) {
      const word = words[i % words.length]
      
      // Determine layer distribution (30% near, 40% mid, 30% far)
      let layer: 'near' | 'mid' | 'far'
      const layerRand = Math.random()
      if (layerRand < 0.3) layer = 'near'
      else if (layerRand < 0.7) layer = 'mid'
      else layer = 'far'

      // Position based on layer depth and avoid UI overlap
      const getLayerBounds = (layer: string) => {
        switch (layer) {
          case 'near': return { x: 8, y: 4, z: [1, 3] }   // Closest layer - closer to camera
          case 'mid': return { x: 10, y: 6, z: [-1, 1] }   // Middle layer  
          case 'far': return { x: 12, y: 8, z: [-3, -1] }  // Farthest layer
          default: return { x: 10, y: 6, z: [-1, 1] }
        }
      }

      const bounds = getLayerBounds(layer)
      
      // Avoid center area where UI elements are positioned
      let x, y
      do {
        x = (Math.random() - 0.5) * bounds.x
        y = (Math.random() - 0.5) * bounds.y
        
        // Avoid center rectangle where main UI is located (-3 to 3 horizontally, -2 to 2 vertically)
      } while (Math.abs(x) < 3 && Math.abs(y) < 2)

      const z = bounds.z[0] + Math.random() * (bounds.z[1] - bounds.z[0])

      instances.push({
        word,
        position: new Vector3(x, y, z),
        scale: layer === 'near' ? 0.8 + Math.random() * 0.4 : // 0.8-1.2
               layer === 'mid' ? 0.6 + Math.random() * 0.3 :   // 0.6-0.9  
               0.4 + Math.random() * 0.2,                      // 0.4-0.6
        phase: Math.random() * Math.PI * 2,
        yawSpeed: (Math.random() - 0.5) * 0.1, // Very small rotation
        glowChance: Math.random() < 0.1 ? 1 : 0, // 10% chance to glow
        layer,
        opacity: layer === 'near' ? 0.8 + Math.random() * 0.2 : // 0.8-1.0
                 layer === 'mid' ? 0.6 + Math.random() * 0.2 :   // 0.6-0.8
                 0.4 + Math.random() * 0.2,                      // 0.4-0.6
      })
    }

    return instances
  }, [wordCount])


  // Always render Bengali words regardless of particle settings
  console.log('BanglaWordField:', { wordCount, instancesCount: wordInstances.length, qualityTier })

  return (
    <group ref={groupRef}>
      {/* Debug mesh */}
      <mesh position={[3, 0, 1]}>
        <sphereGeometry args={[0.1]} />
        <meshBasicMaterial color="#00ff00" />
      </mesh>
      
      {wordInstances.map((instance, index) => (
        <FloatingBengaliText
          key={`${instance.word.bn}-${index}`}
          instance={instance}
          index={index}
        />
      ))}
    </group>
  )
}

// Individual floating text component (memoized for performance)
interface FloatingBengaliTextProps {
  instance: WordInstance
  index: number
}

const FloatingBengaliText = React.memo(function FloatingBengaliText({ instance }: FloatingBengaliTextProps) {
  const textRef = useRef<any>(null)
  const groupRef = useRef<Group>(null)
  

  // Animation
  useFrame((state) => {
    if (!groupRef.current) return

    const time = state.clock.elapsedTime
    
    // Slow sine float
    const floatOffset = Math.sin(time * 0.2 + instance.phase) * 0.5
    groupRef.current.position.y = instance.position.y + floatOffset
    
    // Tiny yaw rotation
    groupRef.current.rotation.y = instance.yawSpeed * time
    
    // Rare glow pulse
    if (instance.glowChance > 0 && textRef.current) {
      const glowIntensity = 0.7 + 0.3 * Math.sin(time * 0.5 + instance.phase)
      // Apply glow effect to material if available
      if (textRef.current.material) {
        (textRef.current.material as any).opacity = instance.opacity * glowIntensity
      }
    }
  })

  // Get color based on layer and word type
  const getTextColor = () => {
    const baseColors = {
      near: instance.word.type === 'verb' ? '#FFB800' : '#FF7A1A',  // Gold for verbs, ember for nouns
      mid: instance.word.type === 'verb' ? '#FFC04D' : '#FF8A50',   // Lighter variants
      far: instance.word.type === 'verb' ? '#FFCC80' : '#FFB380'    // Even lighter for depth
    }
    return baseColors[instance.layer]
  }

  return (
    <group ref={groupRef} position={[instance.position.x, instance.position.y, instance.position.z]}>
      {/* Debug mesh to show position */}
      <mesh>
        <sphereGeometry args={[0.05]} />
        <meshBasicMaterial color={getTextColor()} transparent opacity={0.5} />
      </mesh>
      
      <Text
        ref={textRef}
        font="https://fonts.gstatic.com/s/notosansbengali/v30/Cn-SJsCGWQxOjaGwMQ6fIiMywrNJIky6nvd8BjzVMvJx2mcSPVFpVEqE-6KmsolLicWu8xzI.woff2"
        fontSize={0.18 * instance.scale}
        color={getTextColor()}
        anchorX="center"
        anchorY="middle"
        material-transparent={true}
        material-opacity={instance.opacity}
      >
        {instance.word.bn}
      </Text>
    </group>
  )
})