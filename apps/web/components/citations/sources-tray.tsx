"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronDown, ChevronRight, ExternalLink, Clock, Globe } from "lucide-react"
import { cn } from "../../lib/utils"
import type { Source } from "../../lib/types"

function timeAgo(iso?: string | null): string {
  if (!iso) return ""
  const ts = Date.parse(iso)
  if (Number.isNaN(ts)) return ""
  const deltaSec = Math.max(1, Math.floor((Date.now() - ts) / 1000))
  const minutes = Math.floor(deltaSec / 60)
  const hours = Math.floor(deltaSec / 3600)
  const days = Math.floor(deltaSec / 86400)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

function formatAbsoluteTime(iso?: string | null): string {
  if (!iso) return ""
  const ts = Date.parse(iso)
  if (Number.isNaN(ts)) return ""
  return new Date(ts).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short'
  })
}

function getDomainFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace('www.', '')
  } catch {
    return url
  }
}

function truncateUrl(url: string, maxLength: number = 40): string {
  if (url.length <= maxLength) return url
  return url.substring(0, maxLength - 3) + '...'
}

interface SourceItemProps {
  source: Source
  index: number
  isHighlighted: boolean
  onClick: () => void
  onSourceClick: (url: string) => void
}

function SourceItem({ source, index, isHighlighted, onClick, onSourceClick }: SourceItemProps) {
  const domain = getDomainFromUrl(source.url)
  const relativeTime = timeAgo(source.published_at)
  const absoluteTime = formatAbsoluteTime(source.published_at)
  
  return (
    <motion.div
      className={cn(
        "flex items-start gap-3 p-3 rounded-lg border transition-all duration-200",
        "hover:bg-muted/50 hover:border-primary/20 cursor-pointer",
        isHighlighted && "bg-primary/10 border-primary/30 shadow-sm"
      )}
      onClick={onClick}
      layout
      animate={isHighlighted ? {
        backgroundColor: "hsl(var(--primary)/0.1)",
        borderColor: "hsl(var(--primary)/0.3)"
      } : {}}
      whileHover={{ scale: 1.01 }}
      data-source-index={index}
    >
      {/* Outlet Badge/Icon */}
      <div className="flex-shrink-0">
        {source.logo ? (
          <img
            src={source.logo}
            alt={`${source.name} logo`}
            className="w-8 h-8 rounded-md object-cover bg-muted"
            onError={(e) => {
              // Fallback to initial letter if logo fails to load
              const target = e.target as HTMLImageElement
              target.style.display = 'none'
              target.nextElementSibling?.classList.remove('hidden')
            }}
          />
        ) : null}
        <div 
          className={cn(
            "w-8 h-8 rounded-md flex items-center justify-center text-xs font-bold bg-gradient-to-br from-primary to-accent text-primary-foreground",
            source.logo && "hidden"
          )}
        >
          {source.name?.[0]?.toUpperCase() || "?"}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2 mb-1">
          <h4 className="text-sm font-medium text-foreground line-clamp-2 leading-tight flex-1">
            {source.name || "Untitled"}
          </h4>
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
            {index}
          </div>
        </div>

        {/* Domain */}
        <div className="flex items-center gap-1 mb-1">
          <Globe className="h-3 w-3 text-muted-foreground flex-shrink-0" />
          <span 
            className="text-xs text-muted-foreground truncate max-w-[150px] sm:max-w-[200px]"
            title={source.url}
          >
            {domain}
          </span>
        </div>

        {/* Published Time */}
        {source.published_at && (
          <div className="flex items-center gap-1 mb-2">
            <Clock className="h-3 w-3 text-muted-foreground flex-shrink-0" />
            <span 
              className="text-xs text-muted-foreground"
              title={absoluteTime}
            >
              {relativeTime}
            </span>
          </div>
        )}

        {/* Full URL (truncated with hover) */}
        <div className="flex items-center justify-between">
          <span 
            className="text-xs text-muted-foreground font-mono truncate max-w-[180px] sm:max-w-[250px]"
            title={source.url}
          >
            <span className="hidden sm:inline">{truncateUrl(source.url, 40)}</span>
            <span className="inline sm:hidden">{truncateUrl(source.url, 25)}</span>
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onSourceClick(source.url)
            }}
            className="flex-shrink-0 p-1 hover:bg-muted rounded transition-colors"
            aria-label="Open source in new tab"
          >
            <ExternalLink className="h-3 w-3 text-muted-foreground hover:text-foreground" />
          </button>
        </div>
      </div>
    </motion.div>
  )
}

export interface SourcesTrayProps {
  sources: Source[]
  className?: string
  highlightedSources?: Set<number>
  onMarkerClick?: (index: number) => void
  defaultExpanded?: boolean
}

export function SourcesTray({
  sources,
  className,
  highlightedSources = new Set(),
  onMarkerClick,
  defaultExpanded = false
}: SourcesTrayProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  // Auto-expand when sources are highlighted
  useEffect(() => {
    if (highlightedSources.size > 0) {
      setIsExpanded(true)
    }
  }, [highlightedSources])

  if (!sources || sources.length === 0) return null

  const handleSourceClick = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  const handleItemClick = (index: number) => {
    onMarkerClick?.(index)
  }

  return (
    <div className={cn("mt-4 border-t border-border/50 pt-4", className)}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full text-left group"
        aria-expanded={isExpanded}
        aria-controls="sources-content"
      >
        <div className="flex items-center gap-2">
          <motion.div
            animate={{ rotate: isExpanded ? 90 : 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </motion.div>
          <h3 className="text-sm font-medium text-foreground">
            Sources
          </h3>
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
            {sources.length}
          </span>
        </div>
        <div className="text-xs text-muted-foreground group-hover:text-foreground transition-colors">
          {isExpanded ? 'Collapse' : 'Expand'}
        </div>
      </button>

      {/* Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            id="sources-content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-2 max-h-[400px] overflow-y-auto">
              {sources.map((source, index) => (
                <SourceItem
                  key={`${source.url}-${index}`}
                  source={source}
                  index={index + 1}
                  isHighlighted={highlightedSources.has(index)}
                  onClick={() => handleItemClick(index)}
                  onSourceClick={handleSourceClick}
                />
              ))}
            </div>
            
            {/* Keyboard Shortcuts Hint */}
            <div className="mt-3 pt-3 border-t border-border/30">
              <p className="text-xs text-muted-foreground flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4">
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-muted border border-border rounded text-xs font-mono">
                    [
                  </kbd>
                  <kbd className="px-1.5 py-0.5 bg-muted border border-border rounded text-xs font-mono">
                    ]
                  </kbd>
                  Navigate markers
                </span>
                <span>Click marker to highlight source</span>
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}