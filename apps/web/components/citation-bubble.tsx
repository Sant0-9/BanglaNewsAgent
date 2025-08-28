"use client"

import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ExternalLink, Clock } from "lucide-react"
import type { Source } from "../lib/types"

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

export function CitationBubble({ 
  source, 
  index 
}: { 
  source: Source
  index: number 
}) {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div className="relative inline-block">
      <motion.a
        href={source.url}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold text-blue-600 bg-blue-50 border border-blue-200/70 rounded-full hover:bg-blue-100 hover:border-blue-300 hover:shadow-md transition-all duration-200 cursor-pointer"
        onHoverStart={() => setIsHovered(true)}
        onHoverEnd={() => setIsHovered(false)}
        whileHover={{ scale: 1.15, y: -1 }}
        whileTap={{ scale: 0.9 }}
      >
        {index}
      </motion.a>
      
      <AnimatePresence>
        {isHovered && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-3 w-72 z-50"
          >
            <div className="bg-white rounded-2xl shadow-2xl border border-slate-100 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3">
                {source.logo ? (
                  <img 
                    src={source.logo} 
                    alt={source.name} 
                    className="w-9 h-9 rounded-xl object-cover flex-shrink-0 shadow-sm" 
                  />
                ) : (
                  <div className="w-9 h-9 bg-gradient-to-br from-blue-500 via-purple-600 to-teal-500 rounded-xl flex items-center justify-center text-white font-bold text-sm flex-shrink-0 shadow-lg">
                    {source.name?.[0] || "?"}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-slate-900 text-sm line-clamp-2 mb-1.5">
                    {source.name}
                  </h3>
                  {source.published_at && (
                    <div className="flex items-center gap-1 text-xs text-slate-500 mb-2">
                      <Clock className="w-3 h-3" />
                      {timeAgo(source.published_at)}
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-600 truncate max-w-[180px] font-medium">
                      {new URL(source.url).hostname}
                    </span>
                    <ExternalLink className="w-3.5 h-3.5 text-blue-500" />
                  </div>
                </div>
              </div>
              {/* Modern Arrow */}
              <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-l-transparent border-r-transparent border-t-white drop-shadow-sm"></div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function InlineCitations({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="inline-flex items-center gap-1 ml-1">
      {sources.map((source, index) => (
        <CitationBubble
          key={`${source.url}-${index}`}
          source={source}
          index={index + 1}
        />
      ))}
    </div>
  )
}