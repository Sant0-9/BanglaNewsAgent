"use client"

import { HeroShell } from "./hero-shell"
import { HeroContent } from "./hero-content"
import { DemoBubbles } from "./demo-bubbles" 
import { ThemeToggle } from "../ui/theme-toggle"

export function RedesignedHome() {
  return (
    <div className="relative min-h-screen">
      {/* Theme Toggle - Fixed Position */}
      <div className="fixed top-6 right-6 z-50">
        <ThemeToggle />
      </div>

      {/* Main Hero Section with Glass Frame */}
      <HeroShell>
        <HeroContent />
      </HeroShell>

      {/* Demo Bubbles */}
      <DemoBubbles />
    </div>
  )
}