"use client"

import * as React from "react"
import { cn } from "../../lib/utils"

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number
  indicatorClassName?: string
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, indicatorClassName, style, ...props }, ref) => {
    const progressValue = Math.min(100, Math.max(0, value || 0))
    
    return (
      <div
        ref={ref}
        className={cn(
          "relative h-2 w-full overflow-hidden rounded-full bg-muted",
          className
        )}
        role="progressbar"
        aria-valuenow={progressValue}
        aria-valuemin={0}
        aria-valuemax={100}
        {...props}
      >
        <div
          className={cn(
            "h-full transition-all duration-300 ease-in-out rounded-full",
            indicatorClassName
          )}
          style={{
            width: `${progressValue}%`,
            background: style?.['--progress-foreground'] as string || undefined,
            ...(!style?.['--progress-foreground'] && { 
              backgroundColor: 'hsl(var(--primary))' 
            })
          }}
        />
      </div>
    )
  }
)

Progress.displayName = "Progress"

export { Progress }