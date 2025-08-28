"use client"

import React, { useMemo, useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { motion, AnimatePresence } from "framer-motion"
import { User, Bot, ChevronDown, ChevronUp, Zap, Languages, MoreHorizontal } from "lucide-react"
import type { AskResponse } from "../lib/types"
import { ConfidenceBadge, confidenceLevelFromScore, IntentBadge } from "./badges"
import { DisagreementBanner } from "./disagreement-banner"
import { CitationBubble, InlineCitations } from "./citation-bubble"
import { StreamingText } from "./streaming-text"
import { Button } from "./ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "./ui/dialog"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { API_BASE } from "../lib/config"

function enhanceTextWithCitations(text: string | undefined, sources?: any[]): React.ReactNode {
  if (!text || !sources?.length) return text
  
  // Replace citation markers like [1], [2] with inline citation components
  const citationRegex = /\[(\d+)\]/g
  let lastIndex = 0
  const parts: React.ReactNode[] = []
  let match
  
  while ((match = citationRegex.exec(text)) !== null) {
    // Add text before citation
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    
    // Add citation bubble
    const citationIndex = parseInt(match[1], 10) - 1
    if (sources[citationIndex]) {
      parts.push(
        <CitationBubble
          key={`citation-${match.index}`}
          source={sources[citationIndex]}
          index={citationIndex + 1}
        />
      )
    } else {
      parts.push(match[0]) // Fallback to original text
    }
    
    lastIndex = match.index + match[0].length
  }
  
  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }
  
  return parts.length > 1 ? <>{parts}</> : text
}

export function MessageBubble({
  role,
  userText,
  answer,
  streaming,
  query,
  onAction,
  chunks,
}: {
  role: "user" | "assistant" | "system"
  userText?: string
  answer?: AskResponse
  streaming?: boolean
  query?: string
  onAction?: (action: { type: "deep" | "related" | "english"; payload?: any }) => void
  chunks?: string[]
}) {
  // All hooks must be called before any conditional logic
  const [sourcesOpen, setSourcesOpen] = useState(true)
  const [timelineOpen, setTimelineOpen] = useState(false)
  const [timeline, setTimeline] = useState<null | { date: string; count: number; titles: string[] }[]>(null)
  const [loadingTimeline, setLoadingTimeline] = useState(false)

  if (role === "user") {
    return (
      <motion.div 
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="flex justify-end mb-4"
      >
        <div className="flex items-end gap-3 max-w-[80%]">
          <div className="bg-gradient-to-br from-blue-600 via-purple-600 to-teal-600 rounded-3xl rounded-br-lg px-5 py-3 shadow-xl">
            <p className="text-white text-sm leading-relaxed whitespace-pre-wrap font-medium">
              {userText}
            </p>
          </div>
          <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg">
            <User className="w-3.5 h-3.5 text-white" />
          </div>
        </div>
      </motion.div>
    )
  }

  // assistant bubble
  const confidence = answer?.metrics?.confidence
  const level = confidenceLevelFromScore(confidence)
  const intent = answer?.metrics?.intent

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="flex justify-start mb-4"
    >
      <div className="flex items-start gap-3 max-w-[85%]">
        <div className="w-7 h-7 bg-gradient-to-br from-purple-600 via-blue-600 to-teal-600 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg">
          <Bot className="w-3.5 h-3.5 text-white" />
        </div>
        
        <div className="bg-white rounded-3xl rounded-tl-lg shadow-xl border border-slate-100 px-5 py-4 max-w-full backdrop-blur-sm">
          {/* Header with badges */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-900">KhoborAgent</span>
              {intent && <IntentBadge intent={intent} confidence={confidence} />}
            </div>
            <ConfidenceBadge level={level} />
          </div>

          {/* Main content */}
          <div className="prose prose-slate prose-sm max-w-none">
            <div className="text-slate-800 leading-relaxed text-[15px]">
              {enhanceTextWithCitations(answer?.answer_bn, answer?.sources)}
            </div>
          </div>

          {/* Streaming indicator */}
          {streaming && (
            <div className="flex items-center gap-2 mt-3 text-xs text-slate-500">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
              <span>Thinking...</span>
            </div>
          )}

          {/* Disagreement banner */}
          {answer?.flags?.disagreement && (
            <div className="mt-4">
              <DisagreementBanner />
            </div>
          )}

          {/* Sources summary (compact) */}
          {answer?.sources?.length > 0 && !streaming && (
            <div className="mt-4 pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">Sources</span>
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                    {answer.sources.length}
                  </span>
                </div>
                <button
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                  onClick={() => setSourcesOpen((v) => !v)}
                >
                  {sourcesOpen ? "Hide" : "Show"}
                </button>
              </div>
              
              <AnimatePresence>
                {sourcesOpen && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="flex flex-wrap gap-2 mt-2">
                      {answer.sources.map((source, idx) => (
                        <motion.a
                          key={`${source.url}-${idx}`}
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: idx * 0.05 }}
                          className="flex items-center gap-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-600 hover:text-slate-800 transition-colors"
                        >
                          {source.logo ? (
                            <img src={source.logo} alt={source.name} className="w-4 h-4 rounded object-cover" />
                          ) : (
                            <div className="w-4 h-4 bg-gradient-to-br from-blue-500 to-purple-600 rounded text-white text-[8px] flex items-center justify-center font-bold">
                              {source.name?.[0] || "?"}
                            </div>
                          )}
                          <span className="truncate max-w-[120px]">{source.name}</span>
                          <span className="text-blue-600 font-medium">[{idx + 1}]</span>
                        </motion.a>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Actions */}
          {!streaming && answer && (
            <div className="mt-4 pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    onClick={() => onAction?.({ type: "deep" })}
                  >
                    <Zap className="w-3 h-3" />
                    Deep Dive
                  </motion.button>

                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                    onClick={() => onAction?.({ type: "english" })}
                  >
                    <Languages className="w-3 h-3" />
                    English
                  </motion.button>
                </div>

                {/* Follow-up chips */}
                <div className="flex items-center gap-1">
                  {(answer?.followups || []).slice(0, 2).map((followup, i) => (
                    <motion.button
                      key={i}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      className="px-2 py-1 text-[10px] text-slate-500 bg-slate-100 hover:bg-slate-200 rounded-full transition-colors"
                      onClick={() => onAction?.({ type: "related", payload: followup })}
                    >
                      {followup.slice(0, 20)}...
                    </motion.button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Metrics footer */}
          {answer?.metrics?.intent && answer?.metrics?.confidence !== undefined && (
            <div className="mt-2 text-[10px] text-slate-400 font-mono">
              Route: {answer.metrics.intent} ({answer.metrics.confidence.toFixed(2)})
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}
