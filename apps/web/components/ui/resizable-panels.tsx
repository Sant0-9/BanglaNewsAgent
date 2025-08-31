"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { cn } from "../../lib/utils"

interface ResizablePanelsProps {
  children: [React.ReactNode, React.ReactNode]
  defaultSizePercent?: number
  minSizePercent?: number
  maxSizePercent?: number
  onResize?: (sizePercent: number) => void
  className?: string
  resizerClassName?: string
}

export function ResizablePanels({
  children,
  defaultSizePercent = 25,
  minSizePercent = 15,
  maxSizePercent = 50,
  onResize,
  className,
  resizerClassName
}: ResizablePanelsProps) {
  const [leftSizePercent, setLeftSizePercent] = useState(defaultSizePercent)
  const [isResizing, setIsResizing] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing || !containerRef.current) return

    const containerRect = containerRef.current.getBoundingClientRect()
    const newSizePercent = ((e.clientX - containerRect.left) / containerRect.width) * 100

    // Clamp to min/max
    const clampedSize = Math.max(minSizePercent, Math.min(maxSizePercent, newSizePercent))
    
    setLeftSizePercent(clampedSize)
    onResize?.(clampedSize)
  }, [isResizing, minSizePercent, maxSizePercent, onResize])

  const handleMouseUp = useCallback(() => {
    setIsResizing(false)
  }, [])

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing, handleMouseMove, handleMouseUp])

  return (
    <div ref={containerRef} className={cn("flex h-full", className)}>
      {/* Left Panel */}
      <div 
        style={{ width: `${leftSizePercent}%` }}
        className="overflow-hidden"
      >
        {children[0]}
      </div>

      {/* Resizer */}
      <div
        className={cn(
          "w-1 bg-border hover:bg-primary/20 cursor-col-resize transition-colors relative group",
          isResizing && "bg-primary/30",
          resizerClassName
        )}
        onMouseDown={handleMouseDown}
      >
        {/* Visual indicator */}
        <div className="absolute inset-y-0 left-1/2 w-0.5 bg-border group-hover:bg-primary/50 transition-colors" />
      </div>

      {/* Right Panel */}
      <div 
        style={{ width: `${100 - leftSizePercent}%` }}
        className="overflow-hidden"
      >
        {children[1]}
      </div>
    </div>
  )
}