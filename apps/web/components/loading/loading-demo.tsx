"use client"

import { useState } from "react"
import { Button } from "../ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card"
import { Badge } from "../ui/badge"
import { ThinkingOverlay, GeneratingIndicator } from "../loading"
import { useLoadingSystem } from "../../hooks/use-loading-system"
import { routeAccent, type RouteMode } from "../../lib/loading-accents"
import { cn } from "../../lib/utils"
import { 
  Play, 
  Square, 
  RotateCcw, 
  Settings,
  Eye,
  EyeOff
} from "lucide-react"

const DEMO_MODES: { label: string; mode: RouteMode; color: string }[] = [
  { label: "News", mode: "news", color: "#7C3AED" },
  { label: "Sports", mode: "sports", color: "#10B981" },
  { label: "Markets", mode: "markets", color: "#3B82F6" },
  { label: "Weather", mode: "weather", color: "#06B6D4" },
  { label: "Lookup", mode: "lookup", color: "#F59E0B" },
  { label: "General", mode: "general", color: "#7C3AED" },
]

export function LoadingDemo() {
  const [currentMode, setCurrentMode] = useState<RouteMode>("general")
  const [showReducedMotionDemo, setShowReducedMotionDemo] = useState(false)
  const [generatingVisible, setGeneratingVisible] = useState(false)
  
  const loadingSystem = useLoadingSystem({
    mode: currentMode,
    onStateChange: (state) => {
      console.log(`Demo: Loading state changed to ${state}`)
    },
  })

  const accent = routeAccent(currentMode)

  const startDemo = () => {
    loadingSystem.actions.startThinking()
    setTimeout(() => {
      loadingSystem.actions.startGenerating()
      setGeneratingVisible(true)
    }, 3000)
    setTimeout(() => {
      loadingSystem.actions.complete()
      setGeneratingVisible(false)
    }, 8000)
  }

  const stopDemo = () => {
    loadingSystem.actions.cancel()
    setGeneratingVisible(false)
  }

  const resetDemo = () => {
    loadingSystem.actions.reset()
    setGeneratingVisible(false)
  }

  return (
    <>
      {/* Thinking Overlay */}
      <ThinkingOverlay
        isVisible={loadingSystem.isThinkingVisible}
        mode={currentMode}
        onPhaseChange={loadingSystem.onPhaseChange}
      />

      <div className="min-h-screen bg-background p-8">
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="text-center">
            <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              Loading System Demo
            </h1>
            <p className="text-muted-foreground text-lg">
              Interactive demonstration of the reusable loading system with various modes and accessibility features
            </p>
          </div>

          {/* Controls */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Demo Controls
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Mode Selection */}
              <div>
                <h3 className="text-sm font-medium mb-3">Route Mode</h3>
                <div className="flex flex-wrap gap-2">
                  {DEMO_MODES.map((modeOption) => (
                    <Button
                      key={modeOption.mode}
                      variant={currentMode === modeOption.mode ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentMode(modeOption.mode)}
                      className="h-8"
                      style={currentMode === modeOption.mode ? {
                        background: `linear-gradient(135deg, ${modeOption.color}, ${modeOption.color}CC)`
                      } : {}}
                    >
                      {modeOption.label}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <Button
                  onClick={startDemo}
                  disabled={loadingSystem.state !== 'idle'}
                  className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Start Demo
                </Button>
                <Button
                  onClick={stopDemo}
                  disabled={loadingSystem.state === 'idle'}
                  variant="destructive"
                >
                  <Square className="h-4 w-4 mr-2" />
                  Stop
                </Button>
                <Button onClick={resetDemo} variant="outline">
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Reset
                </Button>
              </div>

              {/* Accessibility Demo Toggle */}
              <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                <div>
                  <h4 className="font-medium">Reduced Motion Demo</h4>
                  <p className="text-sm text-muted-foreground">
                    Toggle to see how animations adapt for accessibility
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowReducedMotionDemo(!showReducedMotionDemo)}
                >
                  {showReducedMotionDemo ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Current State Display */}
          <Card>
            <CardHeader>
              <CardTitle>System State</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <Badge 
                    variant={loadingSystem.state === 'idle' ? 'default' : 'outline'}
                    className="mb-2"
                  >
                    State
                  </Badge>
                  <p className="text-sm font-mono">{loadingSystem.state}</p>
                </div>
                <div className="text-center">
                  <Badge variant="outline" className="mb-2">Phase</Badge>
                  <p className="text-sm font-mono">{loadingSystem.currentPhase}</p>
                </div>
                <div className="text-center">
                  <Badge variant="outline" className="mb-2">Time</Badge>
                  <p className="text-sm font-mono">{(loadingSystem.timeElapsed / 1000).toFixed(1)}s</p>
                </div>
                <div className="text-center">
                  <Badge variant="outline" className="mb-2">Mode</Badge>
                  <p className="text-sm font-mono">{currentMode}</p>
                </div>
              </div>
              
              {loadingSystem.showLongRunningHint && (
                <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                  <p className="text-sm text-amber-600 dark:text-amber-400">
                    Long running hint is now visible (15+ seconds)
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

        </div>
      </div>
    </>
  )
}