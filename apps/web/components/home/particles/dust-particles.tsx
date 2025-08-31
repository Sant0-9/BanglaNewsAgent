"use client"

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { 
  BufferAttribute, 
  BufferGeometry, 
  NormalBlending, 
  Points, 
  ShaderMaterial,
  Vector3
} from 'three'
import { useGraphicsStore } from '../../../lib/stores/graphics-store'

interface DustParticlesProps {
  count?: number
}

// Dust vertex shader
const dustVertexShader = `
uniform float uTime;
uniform float uPixelRatio;

attribute float aScale;
attribute float aOpacity;
attribute vec3 aVelocity;
attribute float aPhase;
attribute float aDriftSpeed;

varying float vOpacity;
varying vec3 vColor;

void main() {
  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
  
  // Apply slow random drift
  vec3 pos = position;
  pos += aVelocity * uTime * aDriftSpeed;
  
  // Add gentle floating motion
  pos.x += sin(uTime * 0.1 + aPhase) * 0.3;
  pos.y += cos(uTime * 0.08 + aPhase * 1.2) * 0.2;
  pos.z += sin(uTime * 0.06 + aPhase * 0.8) * 0.25;
  
  // Keep particles within bounds with wrapping
  pos.x = mod(pos.x + 12.0, 24.0) - 12.0;
  pos.y = mod(pos.y + 8.0, 16.0) - 8.0;
  pos.z = mod(pos.z + 10.0, 20.0) - 10.0;
  
  mvPosition = modelViewMatrix * vec4(pos, 1.0);
  
  // Small, consistent size for dust/stars
  gl_PointSize = aScale * uPixelRatio * (200.0 / -mvPosition.z);
  
  // Distance-based fading
  float distanceFade = 1.0 / (1.0 + length(mvPosition.xyz) * 0.08);
  vOpacity = aOpacity * distanceFade;
  
  // Neutral colors with subtle variation
  float variation = sin(aPhase * 6.28) * 0.1;
  vColor = mix(
    vec3(0.8, 0.85, 0.9),  // Cool white
    vec3(0.9, 0.9, 0.8),   // Warm white
    variation + 0.5
  );
  
  gl_Position = projectionMatrix * mvPosition;
}
`

// Dust fragment shader
const dustFragmentShader = `
varying float vOpacity;
varying vec3 vColor;

void main() {
  // Very small, soft circular particles
  float distanceToCenter = distance(gl_PointCoord, vec2(0.5));
  float alpha = 1.0 - smoothstep(0.0, 0.5, distanceToCenter);
  
  // Subtle sparkle effect for stars
  float sparkle = pow(alpha, 3.0);
  vec3 finalColor = vColor * (0.7 + sparkle * 0.3);
  
  gl_FragColor = vec4(finalColor, alpha * vOpacity * 0.3);
}
`

export function DustParticles({ count: propCount }: DustParticlesProps) {
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
        case 'high': return 75 // Reduced for mobile
        case 'medium': return 50
        case 'low': return 30
        case 'battery': return 15
        default: return 30
      }
    }
    
    // Desktop/tablet counts
    switch (qualityTier) {
      case 'high': return 1200 // 1.2k dust particles for high-end desktop
      case 'medium': return 600 // 600 for medium desktop
      case 'low': return 250 // 250 for low desktop
      case 'battery': return 100 // 100 for battery desktop
      default: return 600
    }
  }, [qualityTier, propCount])

  // Generate particle attributes
  const particleData = useMemo(() => {
    const positions = new Float32Array(particleCount * 3)
    const scales = new Float32Array(particleCount)
    const opacities = new Float32Array(particleCount)
    const velocities = new Float32Array(particleCount * 3)
    const phases = new Float32Array(particleCount)
    const driftSpeeds = new Float32Array(particleCount)

    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3

      // Position: scattered in a larger volume
      positions[i3] = (Math.random() - 0.5) * 20 // x
      positions[i3 + 1] = (Math.random() - 0.5) * 14 // y
      positions[i3 + 2] = (Math.random() - 0.5) * 12 // z

      // Scale: tiny particles
      scales[i] = 2 + Math.random() * 4 // 2-6px base size

      // Opacity: very subtle
      opacities[i] = 0.1 + Math.random() * 0.4

      // Velocity: very slow random drift
      velocities[i3] = (Math.random() - 0.5) * 0.008 // x velocity
      velocities[i3 + 1] = (Math.random() - 0.5) * 0.006 // y velocity
      velocities[i3 + 2] = (Math.random() - 0.5) * 0.007 // z velocity

      // Animation attributes
      phases[i] = Math.random() * Math.PI * 2
      driftSpeeds[i] = 0.5 + Math.random() * 0.8 // Drift speed variation
    }

    return {
      positions,
      scales,
      opacities,
      velocities,
      phases,
      driftSpeeds
    }
  }, [particleCount])

  // Create geometry and material
  const [geometry, material] = useMemo(() => {
    const geo = new BufferGeometry()
    geo.setAttribute('position', new BufferAttribute(particleData.positions, 3))
    geo.setAttribute('aScale', new BufferAttribute(particleData.scales, 1))
    geo.setAttribute('aOpacity', new BufferAttribute(particleData.opacities, 1))
    geo.setAttribute('aVelocity', new BufferAttribute(particleData.velocities, 3))
    geo.setAttribute('aPhase', new BufferAttribute(particleData.phases, 1))
    geo.setAttribute('aDriftSpeed', new BufferAttribute(particleData.driftSpeeds, 1))

    const mat = new ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uPixelRatio: { value: settings.pixelRatio }
      },
      vertexShader: dustVertexShader,
      fragmentShader: dustFragmentShader,
      transparent: true,
      blending: NormalBlending,
      depthWrite: false,
      depthTest: true
    })

    return [geo, mat]
  }, [particleData, settings.pixelRatio])

  // Animation loop with performance monitoring
  useFrame((state, delta) => {
    if (material) {
      material.uniforms.uTime.value = state.clock.elapsedTime * 0.3 // Even slower for dust
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