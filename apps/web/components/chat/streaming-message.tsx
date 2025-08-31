"use client"

import { useEffect, useRef, useState } from "react"
import { MessageBubble } from "./message-bubble"
import { Message } from "../../lib/storage"
import { motion } from "framer-motion"

interface StreamingMessageProps {
  messageId: string
  initialContent?: string
  onComplete?: (content: string) => void
  onStop?: () => void
  onError?: (error: string) => void
  className?: string
}

export function StreamingMessage({ 
  messageId, 
  initialContent = "",
  onComplete,
  onStop,
  onError,
  className 
}: StreamingMessageProps) {
  const [content, setContent] = useState(initialContent)
  const [isStreaming, setIsStreaming] = useState(true)
  const abortControllerRef = useRef<AbortController | null>(null)

  const streamingMessage: Message = {
    id: messageId,
    content,
    role: "assistant",
    timestamp: new Date()
  }

  useEffect(() => {
    return () => {
      // Cleanup: abort any ongoing streaming
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setIsStreaming(false)
    onStop?.()
  }

  const handleComplete = (finalContent: string) => {
    setIsStreaming(false)
    onComplete?.(finalContent)
  }

  const handleError = (error: string) => {
    setIsStreaming(false)
    onError?.(error)
  }

  // Simulate streaming for now (will be replaced with real streaming)
  useEffect(() => {
    if (initialContent && !content) {
      setContent(initialContent)
    }
  }, [initialContent])

  return (
    <MessageBubble
      message={streamingMessage}
      isStreaming={isStreaming}
      onStop={handleStop}
      className={className}
    />
  )
}

interface TypewriterTextProps {
  text: string
  speed?: number
  onComplete?: () => void
  className?: string
}

export function TypewriterText({ 
  text, 
  speed = 20, 
  onComplete, 
  className 
}: TypewriterTextProps) {
  const [displayedText, setDisplayedText] = useState("")
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    if (currentIndex < text.length) {
      const timer = setTimeout(() => {
        setDisplayedText(text.slice(0, currentIndex + 1))
        setCurrentIndex(currentIndex + 1)
      }, speed)

      return () => clearTimeout(timer)
    } else if (currentIndex === text.length && onComplete) {
      onComplete()
    }
  }, [currentIndex, text, speed, onComplete])

  return (
    <span className={className}>
      {displayedText}
      {currentIndex < text.length && (
        <motion.span
          animate={{ opacity: [1, 0, 1] }}
          transition={{ duration: 0.8, repeat: Infinity }}
          className="inline-block w-0.5 h-4 bg-primary ml-0.5"
        />
      )}
    </span>
  )
}

// Hook for handling streaming responses
export function useStreamingResponse() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [content, setContent] = useState("")
  const [error, setError] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const startStream = async (query: string, options: { mode?: string; lang?: string } = {}) => {
    try {
      setIsStreaming(true)
      setContent("") // Start with empty content
      setError(null)

      // Create new abort controller for this stream
      abortControllerRef.current = new AbortController()

      const response = await fetch("/api/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Do not forward UI "mode" values (e.g. "news", "sports") to backend,
        // FastAPI expects only 'brief' | 'deep'. Let the backend default apply.
        body: JSON.stringify({
          query,
          lang: options.lang || 'bn'
        }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error("No response body reader available")
      }

      const decoder = new TextDecoder()
      let accumulatedContent = ""
      let buffer = ""

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ""

          for (const rawLine of lines) {
            const line = rawLine.trim()
            if (!line || !line.startsWith('data: ')) continue

            const jsonStr = line.slice(6).trim()
            if (jsonStr === '[DONE]') {
              setIsStreaming(false)
              return accumulatedContent
            }

            try {
              const evt = JSON.parse(jsonStr)

              // Handle multiple server payload shapes:
              // 1) New backend SSE: { type: 'token'|'chunk'|'complete'|'error'|..., delta?, data? }
              // 2) Fallback simulated stream: { content?, delta? }

              // Error event
              if (evt?.type === 'error') {
                const message = evt?.data?.message || 'Streaming error'
                throw new Error(message)
              }

              // Token/chunk events with delta payload (only accumulate if no complete event expected)
              const delta = evt?.delta ?? evt?.data?.delta
              if (typeof delta === 'string' && delta.length > 0) {
                // Only accumulate tokens if we haven't seen a complete response yet
                accumulatedContent += delta
                
                // Only update displayed content if it looks coherent (not just fragments)
                // Don't show content that looks like random word fragments
                const wordCount = accumulatedContent.trim().split(/\s+/).length
                if (wordCount >= 3 && !accumulatedContent.match(/^[\s\-$]+/)) {
                  setContent(accumulatedContent)
                }
                continue
              }

              // Complete event carries the full payload - ALWAYS use this over accumulated tokens
              if (evt?.type === 'complete') {
                const full = evt?.data?.answer_bn || evt?.data?.answer_en || evt?.data?.content || ''
                if (full) {
                  // Always use complete response, regardless of accumulated content
                  accumulatedContent = full
                  setContent(accumulatedContent)
                  setIsStreaming(false)
                  return accumulatedContent
                }
                continue
              }

              // Fallback shape with top-level content
              if (typeof evt?.content === 'string' && evt.content.length > 0) {
                accumulatedContent += evt.content
                setContent(accumulatedContent)
                continue
              }
            } catch (parseError) {
              console.warn('Failed to parse SSE chunk:', parseError)
            }
          }
        }
      } finally {
        reader.releaseLock()
      }

      setIsStreaming(false)
      return accumulatedContent

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log("Stream aborted by user")
      } else {
        console.error("Streaming error:", err)
        setError(err instanceof Error ? err.message : "Unknown streaming error")
      }
      setIsStreaming(false)
      return null
    }
  }

  const stopStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setIsStreaming(false)
  }

  return {
    isStreaming,
    content,
    error,
    startStream,
    stopStream
  }
}