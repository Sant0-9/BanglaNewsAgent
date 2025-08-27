import { cn } from "@/lib/utils"
import React from "react"

export type ConfidenceLevel = "low" | "medium" | "high"

export function confidenceLevelFromScore(score?: number | null): ConfidenceLevel {
  if (typeof score !== "number" || isNaN(score)) return "medium"
  if (score < 0.5) return "low"
  if (score < 0.8) return "medium"
  return "high"
}

export function ConfidenceBadge({ level, className }: { level: ConfidenceLevel; className?: string }) {
  const styles: Record<ConfidenceLevel, string> = {
    low: "bg-yellow-500/10 text-yellow-400 ring-1 ring-yellow-400/30",
    medium: "bg-yellow-500/20 text-yellow-300 ring-1 ring-yellow-300/30",
    high: "bg-yellow-500/25 text-yellow-200 ring-1 ring-yellow-200/30",
  }

  const label = level === "low" ? "Low" : level === "medium" ? "Med" : "High"

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium tracking-wide shadow-sm",
        styles[level],
        className
      )}
    >
      Confidence: {label}
    </span>
  )
}

const INTENT_LABELS: Record<string, string> = {
  news: "News",
  weather: "Weather",
  markets: "Markets",
  sports: "Sports",
  lookup: "Lookup",
}

export function IntentBadge({ intent, confidence, className }: { intent: string; confidence?: number; className?: string }) {
  const nice = INTENT_LABELS[intent?.toLowerCase?.()] || intent
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-yellow-400/30 bg-white/5 px-2 py-0.5 text-[10px] font-medium text-yellow-300 backdrop-blur-sm",
        className
      )}
      title={typeof confidence === "number" ? `Confidence ${confidence.toFixed(2)}` : undefined}
    >
      {nice}
      {typeof confidence === "number" && <span className="ml-1 opacity-80">({confidence.toFixed(2)})</span>}
    </span>
  )}
