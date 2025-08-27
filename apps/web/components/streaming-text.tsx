"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface StreamingTextProps {
  chunks?: string[]
  text?: string
  isStreaming?: boolean
  className?: string
}

export function StreamingText({ chunks, text, isStreaming = false, className = "" }: StreamingTextProps) {
  const [displayText, setDisplayText] = useState("")
  const [isAnimating, setIsAnimating] = useState(false)
  const animationRef = useRef<number | null>(null)
  const targetTextRef = useRef("")
  const currentIndexRef = useRef(0)

  const startAnimation = useCallback(() => {
    if (isAnimating) return
    
    setIsAnimating(true)
    currentIndexRef.current = displayText.length

    const animate = () => {
      const targetText = targetTextRef.current
      const currentLength = currentIndexRef.current

      if (currentLength < targetText.length) {
        // Add 1-3 characters per frame for smooth but not too slow animation
        const charsToAdd = Math.min(3, targetText.length - currentLength)
        const newText = targetText.slice(0, currentLength + charsToAdd)
        
        setDisplayText(newText)
        currentIndexRef.current += charsToAdd
        
        animationRef.current = requestAnimationFrame(animate)
      } else {
        setIsAnimating(false)
        animationRef.current = null
      }
    }

    animationRef.current = requestAnimationFrame(animate)
  }, [isAnimating, displayText])

  // Determine the target text from chunks or text prop
  useEffect(() => {
    if (chunks && chunks.length > 0) {
      targetTextRef.current = chunks.join("")
    } else if (text) {
      targetTextRef.current = text
    } else {
      targetTextRef.current = ""
    }

    if (isStreaming) {
      startAnimation()
    } else {
      // If not streaming, show final text immediately
      setDisplayText(targetTextRef.current)
      setIsAnimating(false)
    }
  }, [chunks, text, isStreaming, startAnimation])

  // Cleanup animation on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  // If not streaming and we have final text, render as markdown
  if (!isStreaming && !isAnimating && targetTextRef.current) {
    return (
      <div className={className}>
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]}
          components={{
            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
            ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
            li: ({ children }) => <li className="ml-2">{children}</li>,
            code: ({ className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || '')
              return match ? (
                <pre className="bg-dark-800 rounded-lg p-4 overflow-x-auto mb-2">
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              ) : (
                <code className="bg-dark-800 px-1.5 py-0.5 rounded text-sm" {...props}>
                  {children}
                </code>
              )
            },
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-brand-500 pl-4 italic mb-2">
                {children}
              </blockquote>
            ),
            h1: ({ children }) => <h1 className="text-2xl font-bold mb-3">{children}</h1>,
            h2: ({ children }) => <h2 className="text-xl font-bold mb-2">{children}</h2>,
            h3: ({ children }) => <h3 className="text-lg font-bold mb-2">{children}</h3>,
            a: ({ href, children }) => (
              <a href={href} className="text-brand-400 hover:text-brand-300 underline" target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            ),
          }}
        >
          {targetTextRef.current}
        </ReactMarkdown>
      </div>
    )
  }

  // While streaming or animating, show plain text with preserved whitespace
  return (
    <div className={`whitespace-pre-wrap ${className}`}>
      {displayText}
      {(isStreaming || isAnimating) && (
        <span className="animate-pulse">▋</span>
      )}
    </div>
  )
}