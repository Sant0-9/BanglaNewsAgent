"use client"

import { motion } from "framer-motion"
import { cn } from "../../lib/utils"

export interface InlineMarkerProps {
  number: number
  sourceId?: string
  onClick?: () => void
  isHighlighted?: boolean
  className?: string
}

export function InlineMarker({
  number,
  sourceId,
  onClick,
  isHighlighted = false,
  className
}: InlineMarkerProps) {
  // Convert number to circled Unicode character for numbers 1-20
  const getCircledNumber = (num: number): string => {
    if (num >= 1 && num <= 20) {
      // Unicode circled numbers: ① = U+2460, ② = U+2461, etc.
      return String.fromCharCode(0x2460 + num - 1)
    }
    return `${num}` // Fallback for numbers > 20
  }

  return (
    <motion.button
      className={cn(
        "inline-flex items-center justify-center",
        "text-sm font-medium leading-none",
        "text-primary hover:text-primary-foreground",
        "bg-primary/10 hover:bg-primary",
        "border border-primary/20 hover:border-primary",
        "rounded-full transition-all duration-200",
        "focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-1",
        "cursor-pointer select-none",
        isHighlighted && "bg-primary text-primary-foreground border-primary shadow-lg scale-110",
        number <= 20 ? "w-5 h-5 text-base" : "min-w-[20px] h-5 px-1.5 text-xs",
        className
      )}
      onClick={onClick}
      data-source-id={sourceId}
      data-marker-number={number}
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.95 }}
      animate={isHighlighted ? { 
        scale: [1, 1.15, 1], 
        backgroundColor: ["hsl(var(--primary))", "hsl(var(--primary)/0.8)", "hsl(var(--primary))"]
      } : {}}
      transition={{ duration: 0.3, ease: "easeOut" }}
      aria-label={`Source reference ${number}`}
      role="button"
      tabIndex={0}
    >
      {number <= 20 ? getCircledNumber(number) : number}
    </motion.button>
  )
}