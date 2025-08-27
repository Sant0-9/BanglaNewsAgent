"use client"

import React, { useMemo, useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { AskResponse } from "../lib/types"
import { ConfidenceBadge, confidenceLevelFromScore, IntentBadge } from "./badges"
import { DisagreementBanner } from "./disagreement-banner"
import { SourceList } from "./source-list"
import { StreamingText } from "./streaming-text"
import { Button } from "./ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "./ui/dialog"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { API_BASE } from "../lib/config"

function preserveBracketCitations(text: string | undefined): string | undefined {
  if (!text) return text
  // We want to keep tokens like [1] intact. ReactMarkdown will render them as text by default.
  // Ensure we don't automatically convert them to links; we'll rely on default behavior.
  return text
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
      <div className="rounded-2xl px-4 py-3 bg-brand-500 text-white shadow max-w-[85%] ml-auto">
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{userText}</p>
      </div>
    )
  }

  // assistant bubble
  const confidence = answer?.metrics?.confidence
  const level = confidenceLevelFromScore(confidence)
  const intent = answer?.metrics?.intent

  return (
    <div className="relative max-w-[85%] mr-auto">
      <div className="rounded-2xl border border-white/10 bg-[#090826]/70 px-4 py-3 text-white shadow-lg backdrop-blur-md">
        <div className="absolute right-3 top-3">
          <ConfidenceBadge level={level} />
        </div>

        <div className="mb-2 flex items-center gap-2">
          {intent && <IntentBadge intent={intent} confidence={confidence} />}
        </div>

        <div className="prose prose-invert prose-sm max-w-none">
          <StreamingText
            chunks={chunks}
            text={preserveBracketCitations(answer?.answer_bn) || ""}
            isStreaming={streaming}
          />
        </div>

        {/* Metrics subline */}
        {answer?.metrics?.intent && answer?.metrics?.confidence !== undefined && (
          <div className="mt-2 text-[11px] text-white/60">
            Routed: {answer.metrics.intent} ({answer.metrics.confidence.toFixed(2)})
          </div>
        )}

        {answer?.flags?.disagreement && (
          <div className="mt-3">
            <DisagreementBanner />
          </div>
        )}


        {answer?.sources?.length ? (
          <div className="mt-3">
            <div className="mb-2 flex items-center justify-between">
              <div className="text-xs font-medium text-white/80">Sources</div>
              <button
                className="text-xs text-yellow-300 hover:text-yellow-200"
                onClick={() => setSourcesOpen((v) => !v)}
              >
                {sourcesOpen ? "Hide" : "Show"}
              </button>
            </div>
            {sourcesOpen && <SourceList sources={answer.sources} />}
          </div>
        ) : null}

        {streaming && (
          <div className="mt-2 text-[10px] text-white/50">Streaming...</div>
        )}

        {/* Actions */}
        {!streaming && answer && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-8 border-white/15 bg-white/5 text-white hover:bg-white/10"
              onClick={() => onAction?.({ type: "deep" })}
            >
              Deep Dive
            </Button>

            <Dialog open={timelineOpen} onOpenChange={setTimelineOpen}>
              <DialogTrigger asChild>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 border-white/15 bg-white/5 text-white hover:bg-white/10"
                  onClick={async () => {
                    try {
                      if (!answer?.metrics?.intent) {
                        // optimistic open
                      }
                      setTimelineOpen(true)
                      setLoadingTimeline(true)
                      const q = encodeURIComponent(query || userText || "")
                      const res = await fetch(`${API_BASE}/timeline?query=${q}&days=7`)
                      if (!res.ok) throw new Error("Timeline API missing")
                      const data = await res.json()
                      setTimeline(data?.items || [])
                    } catch (e) {
                      toast("Coming soon")
                    } finally {
                      setLoadingTimeline(false)
                    }
                  }}
                >
                  Timeline
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Timeline (7 days)</DialogTitle>
                </DialogHeader>
                <div className="max-h-[60vh] overflow-y-auto">
                  {loadingTimeline ? (
                    <div className="py-8 text-center text-white/70">Loading…</div>
                  ) : !timeline || timeline.length === 0 ? (
                    <div className="py-8 text-center text-white/70">No data</div>
                  ) : (
                    <div className="space-y-3">
                      {timeline.map((d, i) => (
                        <div key={i} className="rounded-xl border border-white/10 bg-white/5 p-3">
                          <div className="flex items-center justify-between text-sm">
                            <div className="font-medium text-white">{d.date}</div>
                            <div className="text-white/70">{d.count} items</div>
                          </div>
                          <ul className="mt-2 list-disc pl-5 text-sm text-white/80">
                            {d.titles.slice(0, 5).map((t, ti) => (
                              <li key={ti} className="truncate">{t}</li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </DialogContent>
            </Dialog>

            {/* Related - placeholder chips */}
            <div className="flex flex-wrap gap-2">
              {(answer?.followups || []).slice(0, 6).map((r, i) => (
                <button
                  key={i}
                  className="rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-[11px] text-white hover:bg-white/10"
                  onClick={() => onAction?.({ type: "related", payload: r })}
                >
                  {r}
                </button>
              ))}
            </div>

            <Button
              size="sm"
              variant="outline"
              className="h-8 border-white/15 bg-white/5 text-white hover:bg-white/10"
              onClick={() => onAction?.({ type: "english" })}
            >
              English
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
