"use client"

import { cn } from "@/lib/utils"

interface LoadingSkeletonProps {
  className?: string
}

export function LoadingSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div className={cn("relative max-w-[85%] mr-auto", className)}>
      <div className="rounded-2xl border border-white/10 bg-[#090826]/70 px-4 py-3 text-white shadow-lg backdrop-blur-md">
        {/* Header skeleton */}
        <div className="mb-3 flex items-center gap-2">
          <div className="h-5 w-16 rounded-full bg-white/10 animate-pulse" />
          <div className="h-4 w-12 rounded bg-white/5 animate-pulse" />
        </div>

        {/* Content skeleton with shimmer effect */}
        <div className="space-y-3">
          <div className="space-y-2">
            <div className="h-4 w-full rounded bg-gradient-to-r from-white/5 via-white/10 to-white/5 bg-[length:200%_100%] animate-shimmer" />
            <div className="h-4 w-4/5 rounded bg-gradient-to-r from-white/5 via-white/10 to-white/5 bg-[length:200%_100%] animate-shimmer [animation-delay:0.1s]" />
            <div className="h-4 w-3/4 rounded bg-gradient-to-r from-white/5 via-white/10 to-white/5 bg-[length:200%_100%] animate-shimmer [animation-delay:0.2s]" />
          </div>
          
          <div className="space-y-2">
            <div className="h-4 w-full rounded bg-gradient-to-r from-white/5 via-white/10 to-white/5 bg-[length:200%_100%] animate-shimmer [animation-delay:0.3s]" />
            <div className="h-4 w-5/6 rounded bg-gradient-to-r from-white/5 via-white/10 to-white/5 bg-[length:200%_100%] animate-shimmer [animation-delay:0.4s]" />
          </div>
        </div>

        {/* Footer skeleton */}
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between">
            <div className="h-3 w-12 rounded bg-white/5 animate-pulse" />
            <div className="h-3 w-8 rounded bg-white/5 animate-pulse" />
          </div>
          <div className="flex gap-2">
            <div className="h-6 w-20 rounded-full bg-white/5 animate-pulse" />
            <div className="h-6 w-16 rounded-full bg-white/5 animate-pulse" />
          </div>
        </div>

        {/* Streaming indicator */}
        <div className="mt-3 flex items-center gap-2">
          <div className="flex space-x-1">
            <div className="h-2 w-2 rounded-full bg-brand-400 animate-bounce [animation-delay:-0.3s]" />
            <div className="h-2 w-2 rounded-full bg-brand-400 animate-bounce [animation-delay:-0.15s]" />
            <div className="h-2 w-2 rounded-full bg-brand-400 animate-bounce" />
          </div>
          <div className="text-xs text-white/50">Thinking...</div>
        </div>
      </div>
    </div>
  )
}