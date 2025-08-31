"use client"

import { AlertTriangle, Info } from "lucide-react"
import { cn } from "../../lib/utils"

export interface ConfidenceIndicatorProps {
  confidence?: number
  className?: string
  showAlways?: boolean
}

export function ConfidenceIndicator({ 
  confidence, 
  className,
  showAlways = false 
}: ConfidenceIndicatorProps) {
  // Only show for low confidence (< 0.6) unless showAlways is true
  if (!confidence || (!showAlways && confidence >= 0.6)) return null

  const confidenceLevel = confidence < 0.4 ? 'very-low' : confidence < 0.6 ? 'low' : 'medium'
  
  const variants = {
    'very-low': {
      label: 'Very Low Confidence',
      shortLabel: 'Low confidence',
      icon: AlertTriangle,
      className: 'bg-red-500/10 text-red-600 border-red-500/20 hover:bg-red-500/20 dark:text-red-400',
      iconColor: 'text-red-500 dark:text-red-400'
    },
    'low': {
      label: 'Low Confidence',
      shortLabel: 'Low confidence',
      icon: AlertTriangle,
      className: 'bg-amber-500/10 text-amber-600 border-amber-500/20 hover:bg-amber-500/20 dark:text-amber-400',
      iconColor: 'text-amber-500 dark:text-amber-400'
    },
    'medium': {
      label: 'Medium Confidence',
      shortLabel: 'Medium confidence',
      icon: Info,
      className: 'bg-fire-ember/10 text-fire-ember border-fire-ember/20 hover:bg-fire-ember/20',
      iconColor: 'text-fire-ember'
    }
  }

  const variant = variants[confidenceLevel]
  const Icon = variant.icon
  const percentage = Math.round(confidence * 100)

  return (
    <div 
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded-full border text-xs font-medium transition-colors",
        variant.className,
        className
      )}
      title={`${variant.label}: ${percentage}% confidence in this response`}
      role="status"
      aria-label={`${variant.shortLabel}: ${percentage}%`}
    >
      <Icon className={cn("h-3 w-3", variant.iconColor)} />
      <span className="hidden sm:inline">{variant.shortLabel}</span>
      <span className="font-mono">{percentage}%</span>
    </div>
  )
}