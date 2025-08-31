"use client"

import { forwardRef } from "react"
import { InlineMarker } from "./inline-marker"
import { SourcesTray } from "./sources-tray"
import { ConfidenceIndicator } from "./confidence-indicator"
import { useCitationSystem } from "../../hooks/use-citation-system"
import { cn } from "../../lib/utils"
import type { Source } from "../../lib/types"

export interface CitationSystemProps {
  sources: Source[]
  confidence?: number
  messageId?: string
  content: string
  className?: string
  showConfidenceAlways?: boolean
  defaultSourcesExpanded?: boolean
  enableKeyboardNavigation?: boolean
}

// Helper function to insert markers into text
function insertCitationMarkers(content: string, sources: Source[], onMarkerClick: (index: number) => void): React.ReactNode[] {
  if (!sources || sources.length === 0) {
    return [content]
  }

  // For now, we'll add markers at the end of sentences
  // In a real implementation, you'd have marker positions from the API
  const sentences = content.split(/([.!?]+\s+)/)
  const result: React.ReactNode[] = []
  let sourceIndex = 0
  
  sentences.forEach((sentence, idx) => {
    result.push(<span key={`text-${idx}`}>{sentence}</span>)
    
    // Add markers after sentences (not punctuation)
    if (sentence.trim() && !sentence.match(/^[.!?]+\s*$/) && sourceIndex < sources.length) {
      // Add multiple markers if there are enough sources
      const markersToAdd = Math.min(Math.ceil(sources.length / (sentences.length / 2)), sources.length - sourceIndex)
      
      for (let i = 0; i < markersToAdd && sourceIndex < sources.length; i++) {
        result.push(
          <InlineMarker
            key={`marker-${sourceIndex}`}
            number={sourceIndex + 1}
            sourceId={`${sources[sourceIndex].url}-${sourceIndex}`}
            onClick={() => onMarkerClick(sourceIndex)}
            className="ml-1"
          />
        )
        sourceIndex++
      }
    }
  })
  
  // Add any remaining markers at the very end
  while (sourceIndex < sources.length) {
    result.push(
      <InlineMarker
        key={`marker-end-${sourceIndex}`}
        number={sourceIndex + 1}
        sourceId={`${sources[sourceIndex].url}-${sourceIndex}`}
        onClick={() => onMarkerClick(sourceIndex)}
        className="ml-1"
      />
    )
    sourceIndex++
  }
  
  return result
}

export const CitationSystem = forwardRef<HTMLDivElement, CitationSystemProps>(
  ({
    sources,
    confidence,
    messageId,
    content,
    className,
    showConfidenceAlways = false,
    defaultSourcesExpanded = false,
    enableKeyboardNavigation = true
  }, ref) => {
    const citationSystem = useCitationSystem({
      sources,
      messageId,
      enableKeyboardNavigation
    })

    // Render content with inline markers
    const contentWithMarkers = insertCitationMarkers(
      content,
      sources,
      citationSystem.handleMarkerClick
    )

    return (
      <div
        ref={(node) => {
          citationSystem.containerRef.current = node
          if (typeof ref === 'function') ref(node)
          else if (ref) ref.current = node
        }}
        className={cn("citation-system", className)}
        data-message-id={messageId}
        tabIndex={citationSystem.hasKeyboardNavigation ? 0 : undefined}
        role={citationSystem.hasKeyboardNavigation ? "region" : undefined}
        aria-label={citationSystem.hasKeyboardNavigation ? "Message with citations - use [ and ] to navigate" : undefined}
      >
        {/* Message Header with Confidence Indicator */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {/* Low confidence indicator */}
            <ConfidenceIndicator 
              confidence={confidence} 
              showAlways={showConfidenceAlways}
            />
          </div>
          
          {/* Navigation Hint */}
          {citationSystem.hasKeyboardNavigation && (
            <div className="text-xs text-muted-foreground hidden sm:block">
              Use <kbd className="px-1 py-0.5 bg-muted border border-border rounded font-mono">
                [
              </kbd> and <kbd className="px-1 py-0.5 bg-muted border border-border rounded font-mono">
                ]
              </kbd> to navigate citations
            </div>
          )}
        </div>

        {/* Message Content with Inline Markers */}
        <div className="text-base leading-relaxed">
          {contentWithMarkers}
        </div>

        {/* Sources Tray */}
        {sources && sources.length > 0 && (
          <SourcesTray
            sources={sources}
            highlightedSources={citationSystem.highlightedSources}
            onMarkerClick={citationSystem.handleSourceClick}
            defaultExpanded={defaultSourcesExpanded}
          />
        )}
      </div>
    )
  }
)

CitationSystem.displayName = "CitationSystem"