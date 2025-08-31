"use client"

import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import { 
  AdditiveBlending, 
  BufferAttribute, 
  BufferGeometry, 
  Color, 
  InstancedBufferAttribute, 
  InstancedBufferGeometry, 
  Points, 
  ShaderMaterial,
  Vector3
} from 'three'
import { useGraphicsStore } from '../../../lib/stores/graphics-store'

interface EmberParticlesProps {
  count?: number
}

// Ember vertex shader
const emberVertexShader = `
uniform float uTime;
uniform float uPixelRatio;

attribute float aScale;
attribute float aOpacity;
attribute vec3 aVelocity;
attribute float aLifetime;
attribute float aPhase;
attribute float aFlickerSpeed;

varying float vOpacity;
varying vec3 vColor;

void main() {
  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
  
  // Apply velocity and time-based movement
  vec3 pos = position;
  pos += aVelocity * uTime;
  
  // Slow updraft with slight horizontal drift
  pos.y += sin(uTime * 0.3 + aPhase) * 0.1 + uTime * 0.02;
  pos.x += sin(uTime * 0.2 + aPhase * 1.3) * 0.05;
  pos.z += cos(uTime * 0.15 + aPhase * 0.7) * 0.03;
  
  // Reset particles that drift too far
  pos.y = mod(pos.y + 10.0, 20.0) - 10.0;
  
  mvPosition = modelViewMatrix * vec4(pos, 1.0);
  
  // Size flickering effect
  float flicker = 0.8 + 0.4 * sin(uTime * aFlickerSpeed + aPhase);
  gl_PointSize = aScale * flicker * uPixelRatio * (300.0 / -mvPosition.z);
  
  // Fade based on lifetime and distance
  float lifeFade = 1.0 - smoothstep(0.8, 1.0, aLifetime);
  float distanceFade = 1.0 / (1.0 + length(mvPosition.xyz) * 0.1);
  vOpacity = aOpacity * lifeFade * distanceFade;
  
  // Warm ember colors with slight variation
  float colorVariation = sin(aPhase * 3.14159) * 0.3;
  vColor = mix(
    vec3(1.0, 0.4, 0.0),  // Fire molten
    vec3(1.0, 0.6, 0.1),  // Fire ember
    colorVariation
  );
  
  gl_Position = projectionMatrix * mvPosition;
}
`

// Ember fragment shader
const emberFragmentShader = `
varying float vOpacity;
varying vec3 vColor;

void main() {
  // Circular particle shape with soft edges
  float distanceToCenter = distance(gl_PointCoord, vec2(0.5));
  float alpha = 1.0 - smoothstep(0.0, 0.5, distanceToCenter);
  
  // Add inner glow effect
  float glow = 1.0 - smoothstep(0.0, 0.3, distanceToCenter);
  vec3 finalColor = vColor + vec3(0.3, 0.2, 0.0) * glow;
  
  // Reduce opacity to prevent overbloom
  gl_FragColor = vec4(finalColor, alpha * vOpacity * 0.4);
}
`

export function EmberParticles({ count: propCount }: EmberParticlesProps) {
  const meshRef = useRef<Points>(null)
  const { settings, qualityTier } = useGraphicsStore()

  // Determine particle count based on quality tier and mobile detection
  const particleCount = useMemo(() => {
    if (propCount) return propCount
    
    // Check for mobile device
    const isMobile = typeof window !== 'undefined' && (
      /Mobile|Android|iPhone|iPad/.test(navigator.userAgent) ||
      window.innerWidth < 768
    )
    
    if (isMobile) {
      // Mobile-specific counts (much lower)
      switch (qualityTier) {
        case 'high': return 100 // Reduced for mobile
        case 'medium': return 75
        case 'low': return 50
        case 'battery': return 25
        default: return 50
      }
    }
    
    // Desktop/tablet counts
    switch (qualityTier) {
      case 'high': return 1500 // 1.5k embers for high-end desktop
      case 'medium': return 800 // 800 for medium desktop
      case 'low': return 300 // 300 for low desktop
      case 'battery': return 150 // 150 for battery desktop
      default: return 800
    }
  }, [qualityTier, propCount])

  // Generate particle attributes
  const particleData = useMemo(() => {
    const positions = new Float32Array(particleCount * 3)
    const scales = new Float32Array(particleCount)
    const opacities = new Float32Array(particleCount)
    const velocities = new Float32Array(particleCount * 3)
    const lifetimes = new Float32Array(particleCount)
    const phases = new Float32Array(particleCount)
    const flickerSpeeds = new Float32Array(particleCount)

    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3

      // Position: scattered in a volume
      positions[i3] = (Math.random() - 0.5) * 16 // x
      positions[i3 + 1] = (Math.random() - 0.5) * 12 - 2 // y (biased downward)
      positions[i3 + 2] = (Math.random() - 0.5) * 8 // z

      // Scale: varied ember sizes
      scales[i] = 8 + Math.random() * 12 // 8-20px base size

      // Opacity: reduced to prevent overbloom
      opacities[i] = 0.2 + Math.random() * 0.4

      // Velocity: slow upward drift with horizontal variation
      velocities[i3] = (Math.random() - 0.5) * 0.02 // x velocity
      velocities[i3 + 1] = 0.01 + Math.random() * 0.02 // y velocity (upward)
      velocities[i3 + 2] = (Math.random() - 0.5) * 0.015 // z velocity

      // Lifecycle attributes
      lifetimes[i] = Math.random()
      phases[i] = Math.random() * Math.PI * 2
      flickerSpeeds[i] = 1.5 + Math.random() * 2.0 // Flicker rate variation
    }

    return {
      positions,
      scales,
      opacities,
      velocities,
      lifetimes,
      phases,
      flickerSpeeds
    }
  }, [particleCount])

  // Create geometry and material
  const [geometry, material] = useMemo(() => {
    const geo = new BufferGeometry()
    geo.setAttribute('position', new BufferAttribute(particleData.positions, 3))
    geo.setAttribute('aScale', new BufferAttribute(particleData.scales, 1))
    geo.setAttribute('aOpacity', new BufferAttribute(particleData.opacities, 1))
    geo.setAttribute('aVelocity', new BufferAttribute(particleData.velocities, 3))
    geo.setAttribute('aLifetime', new BufferAttribute(particleData.lifetimes, 1))
    geo.setAttribute('aPhase', new BufferAttribute(particleData.phases, 1))
    geo.setAttribute('aFlickerSpeed', new BufferAttribute(particleData.flickerSpeeds, 1))

    const mat = new ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uPixelRatio: { value: settings.pixelRatio }
      },
      vertexShader: emberVertexShader,
      fragmentShader: emberFragmentShader,
      transparent: true,
      blending: AdditiveBlending,
      depthWrite: false,
      depthTest: true
    })

    return [geo, mat]
  }, [particleData, settings.pixelRatio])

  // Animation loop with performance monitoring
  useFrame((state, delta) => {
    if (material) {
      material.uniforms.uTime.value = state.clock.elapsedTime * 0.5 // Slow time for embers
    }
    
    // Performance-based LOD: reduce update frequency on low FPS
    if (delta > 1/30) { // If frame time > 33ms (less than 30 FPS)
      // Skip some animation updates to maintain performance
      return
    }
  })

  // Only render if particles are enabled
  if (!settings.enableParticles) {
    return null
  }

  return (
    <points ref={meshRef} geometry={geometry} material={material} />
  )
}