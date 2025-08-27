"use client"

import { Button } from "./ui/button"
import { MessageCircle, Sparkles } from "lucide-react"

const SUGGESTED_PROMPTS = [
  "Latest on semiconductor export controls",
  "Bangladesh inflation this week", 
  "NVIDIA earnings preview"
]

interface EmptyStateProps {
  onPromptSelect: (prompt: string) => void
}

export function EmptyState({ onPromptSelect }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div className="text-center space-y-6 max-w-lg">
        {/* Icon */}
        <div className="relative">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-brand-500/20 border border-brand-500/30">
            <MessageCircle className="w-8 h-8 text-brand-400" />
          </div>
          <div className="absolute -top-1 -right-1">
            <Sparkles className="w-5 h-5 text-yellow-400" />
          </div>
        </div>

        {/* Heading */}
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-white">
            Ask KhoborAgent
          </h2>
          <p className="text-white/70 text-sm">
            Get fresh news, market updates, and insights in Bangla or English
          </p>
        </div>

        {/* Suggested Prompts */}
        <div className="space-y-3">
          <p className="text-xs font-medium text-white/60 uppercase tracking-wider">
            Try asking about:
          </p>
          <div className="space-y-2">
            {SUGGESTED_PROMPTS.map((prompt, index) => (
              <Button
                key={index}
                variant="outline"
                className="w-full justify-start text-left h-auto p-4 border-white/15 bg-white/5 text-white hover:bg-white/10 hover:border-brand-500/30 transition-all duration-200"
                onClick={() => onPromptSelect(prompt)}
              >
                <div className="text-sm">{prompt}</div>
              </Button>
            ))}
          </div>
        </div>

        {/* Hint */}
        <div className="text-xs text-white/50">
          Ask in English or Bangla • Get fresh insights with citations
        </div>
      </div>
    </div>
  )
}