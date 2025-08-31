"use client"

import { useState, useCallback, useRef } from "react"
import { Button } from "../ui/button"
import { Card, CardContent } from "../ui/card"
import { Badge } from "../ui/badge"
import { Textarea } from "../ui/textarea"
import { ThemeToggle } from "../ui/theme-toggle"
import { ThinkingOverlay, GeneratingIndicator } from "../loading"
import { useChat } from "../../contexts/chat-context"
import { useLoadingSystem } from "../../hooks/use-loading-system"
import { routeAccent, type RouteMode } from "../../lib/loading-accents"
import { cn } from "../../lib/utils"
import { formatTime } from "../../lib/utils"
import { 
  Send, 
  Bot, 
  User, 
  Newspaper, 
  Sparkles, 
  ChevronRight, 
  Clock, 
  ExternalLink,
  X,
  AlertCircle
} from "lucide-react"

const SAMPLE_QUERIES = [
  { query: "আজকের সর্বশেষ খবর কী?", category: "News", icon: "📰", mode: "news" as RouteMode },
  { query: "বাংলাদেশের আর্থিক অবস্থা", category: "Economy", icon: "💰", mode: "markets" as RouteMode },
  { query: "ঢাকার আবহাওয়া কেমন?", category: "Weather", icon: "🌤️", mode: "weather" as RouteMode },
  { query: "ক্রিকেট ম্যাচের খবর", category: "Sports", icon: "🏏", mode: "sports" as RouteMode },
]

export function EnhancedChatInterface() {
  const { activeConversation, addMessage, currentMode } = useChat()
  const [input, setInput] = useState("")
  const [lang, setLang] = useState<"bn" | "en">("bn")
  const [currentRequestMode, setCurrentRequestMode] = useState<RouteMode>("general")
  const [generatingMessageId, setGeneratingMessageId] = useState<string | null>(null)
  
  const abortControllerRef = useRef<AbortController | null>(null)
  
  // Initialize loading system
  const loadingSystem = useLoadingSystem({
    mode: currentRequestMode,
    onStateChange: (state) => {
      console.log(`Loading state changed to: ${state}`)
    },
    onPhaseChange: (phase) => {
      console.log(`Phase changed to: ${phase}`)
    },
    longRunningThreshold: 15000
  })

  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    loadingSystem.actions.cancel()
    setGeneratingMessageId(null)
  }, [loadingSystem.actions])

  const detectRequestMode = useCallback((query: string): RouteMode => {
    const queryLower = query.toLowerCase()
    const banglaQueryLower = query.toLowerCase()
    
    // News keywords
    if (queryLower.includes('news') || queryLower.includes('খবর') || 
        banglaQueryLower.includes('সংবাদ') || queryLower.includes('breaking')) {
      return 'news'
    }
    
    // Sports keywords  
    if (queryLower.includes('sport') || queryLower.includes('cricket') || 
        queryLower.includes('football') || banglaQueryLower.includes('খেলা') ||
        banglaQueryLower.includes('ক্রিকেট')) {
      return 'sports'
    }
    
    // Weather keywords
    if (queryLower.includes('weather') || queryLower.includes('temperature') ||
        banglaQueryLower.includes('আবহাওয়া') || banglaQueryLower.includes('বৃষ্টি')) {
      return 'weather'
    }
    
    // Markets keywords
    if (queryLower.includes('market') || queryLower.includes('stock') ||
        queryLower.includes('price') || banglaQueryLower.includes('বাজার') ||
        banglaQueryLower.includes('অর্থনীতি')) {
      return 'markets'
    }
    
    return 'general'
  }, [])

  const sendMessage = async (query?: string, predefinedMode?: RouteMode) => {
    const messageContent = query || input.trim()
    if (!messageContent || loadingSystem.state !== 'idle') return

    // Detect or use predefined mode
    const detectedMode = predefinedMode || detectRequestMode(messageContent)
    setCurrentRequestMode(detectedMode)
    
    const userMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substring(7)}`,
      content: messageContent,
      role: "user" as const,
      timestamp: new Date()
    }

    // Add user message immediately
    addMessage(userMessage)
    setInput("")
    
    // Start thinking phase
    loadingSystem.actions.startThinking()
    
    // Create abort controller for this request
    abortControllerRef.current = new AbortController()

    try {
      // Simulate phase events (in real implementation, these would come from the API)
      const phaseTimeouts: NodeJS.Timeout[] = []
      
      phaseTimeouts.push(setTimeout(() => {
        loadingSystem.actions.addPhaseEvent('fetching')
      }, 300))
      
      phaseTimeouts.push(setTimeout(() => {
        loadingSystem.actions.addPhaseEvent('deduping')
      }, 800))
      
      phaseTimeouts.push(setTimeout(() => {
        loadingSystem.actions.addPhaseEvent('reranking')
      }, 1200))
      
      phaseTimeouts.push(setTimeout(() => {
        loadingSystem.actions.addPhaseEvent('summarizing')
      }, 1600))

      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Backend accepts only { query, lang }. Do not forward UI mode.
        body: JSON.stringify({ 
          query: messageContent, 
          lang
        }),
        signal: abortControllerRef.current.signal
      })

      // Clear phase timeouts
      phaseTimeouts.forEach(clearTimeout)

      if (response.ok) {
        // Switch to generating phase
        const assistantMessageId = `msg_${Date.now() + 1}_${Math.random().toString(36).substring(7)}`
        setGeneratingMessageId(assistantMessageId)
        loadingSystem.actions.startGenerating()

        // Check if response is streaming
        const contentType = response.headers.get('content-type')
        if (contentType?.includes('text/stream')) {
          // Handle streaming response
          const reader = response.body?.getReader()
          const decoder = new TextDecoder()
          let content = ""

          if (reader) {
            while (true) {
              const { done, value } = await reader.read()
              if (done) break
              
              content += decoder.decode(value, { stream: true })
            }
          }

          const assistantMessage = {
            id: assistantMessageId,
            content: content,
            role: "assistant" as const,
            timestamp: new Date(),
            intent: detectedMode,
            confidence: 0.9
          }
          addMessage(assistantMessage)
        } else {
          // Handle regular JSON response
          const data = await response.json()
          const assistantMessage = {
            id: assistantMessageId,
            content: data.answer_bn || data.answer_en,
            role: "assistant" as const,
            timestamp: new Date(),
            intent: data.metrics?.intent || detectedMode,
            confidence: data.metrics?.confidence || 0.8,
            sources: data.sources
          }
          addMessage(assistantMessage)
        }
      } else {
        throw new Error("Failed to get response")
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        // Request was cancelled - don't show error message
        return
      }
      
      const errorMessage = {
        id: `msg_${Date.now() + 1}_${Math.random().toString(36).substring(7)}`,
        content: "দুঃখিত, কিছু সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
        role: "assistant" as const,
        timestamp: new Date(),
        intent: "error",
        confidence: 0
      }
      addMessage(errorMessage)
    } finally {
      loadingSystem.actions.stop()
      setGeneratingMessageId(null)
      abortControllerRef.current = null
    }
  }

  const messages = activeConversation?.messages || []
  const accent = routeAccent(currentRequestMode)

  return (
    <>
      {/* Thinking Overlay */}
      <ThinkingOverlay
        isVisible={loadingSystem.isThinkingVisible}
        mode={currentRequestMode}
        onPhaseChange={loadingSystem.onPhaseChange}
      />

      <div className="flex-1 flex flex-col h-full">
        {/* Sticky Header */}
        <header className="bg-card/80 backdrop-blur-xl border-b border-border sticky top-0 z-40 shadow-sm">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div 
                  className="w-8 h-8 rounded-xl flex items-center justify-center"
                  style={{ 
                    background: `linear-gradient(135deg, ${accent.primary}, ${accent.secondary})` 
                  }}
                >
                  <Newspaper className="h-4 w-4 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                    KhoborAgent
                  </h1>
                  <p className="text-xs text-muted-foreground">AI সংবাদ সহায়ক</p>
                </div>
              </div>
              
              <div className="flex items-center space-x-3">
                {/* Cancel button when loading */}
                {loadingSystem.state !== 'idle' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={cancelRequest}
                    className="h-8 px-3 text-xs border-destructive/50 text-destructive hover:bg-destructive/10"
                  >
                    <X className="h-3 w-3 mr-1" />
                    Cancel
                  </Button>
                )}
                
                {/* Long running hint */}
                {loadingSystem.showLongRunningHint && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/50 rounded-lg px-3 py-1">
                    <AlertCircle className="h-3 w-3" />
                    Still working… this can take a moment.
                  </div>
                )}

                <div className="flex items-center bg-muted rounded-xl p-1">
                  <Button
                    variant={lang === "bn" ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setLang("bn")}
                    className="h-8 px-4 text-xs rounded-lg font-medium"
                    disabled={loadingSystem.state !== 'idle'}
                  >
                    বাংলা
                  </Button>
                  <Button
                    variant={lang === "en" ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setLang("en")}
                    className="h-8 px-4 text-xs rounded-lg font-medium"
                    disabled={loadingSystem.state !== 'idle'}
                  >
                    English
                  </Button>
                </div>
                <ThemeToggle />
                <Badge className="bg-green-500/10 text-green-400 border-green-500/20 px-3 py-1 rounded-full">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                  অনলাইন
                </Badge>
              </div>
            </div>
          </div>
        </header>

        {/* Chat Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 py-8">
            {/* Welcome Section or Messages */}
            {messages.length === 0 ? (
              <div className="text-center mb-12">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary to-accent rounded-3xl mb-6 shadow-xl">
                  <Sparkles className="h-10 w-10 text-primary-foreground" />
                </div>
                <h2 className="text-4xl font-bold text-foreground mb-4">
                  আপনার ব্যক্তিগত সংবাদ সহায়ক
                </h2>
                <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
                  সর্বশেষ সংবাদ, আবহাওয়া, শেয়ার বাজার এবং খেলাধুলার খবর পান আপনার ভাষায়
                </p>
                
                {/* Quick Actions */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl mx-auto mb-12">
                  {SAMPLE_QUERIES.map((item, index) => (
                    <Card 
                      key={index}
                      className="group cursor-pointer border-border hover:border-primary/50 hover:shadow-xl transition-all duration-300 bg-card/50 backdrop-blur-sm hover:scale-[1.02]"
                      onClick={() => sendMessage(item.query, item.mode)}
                    >
                      <CardContent className="p-6">
                        <div className="flex items-center justify-between">
                          <div className="text-left">
                            <div className="flex items-center gap-3 mb-3">
                              <span className="text-2xl">{item.icon}</span>
                              <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 px-3 py-1">
                                {item.category}
                              </Badge>
                            </div>
                            <p className="text-lg text-foreground group-hover:text-primary transition-colors font-medium">
                              {item.query}
                            </p>
                          </div>
                          <ChevronRight className="h-6 w-6 text-muted-foreground group-hover:text-primary transition-colors ml-4" />
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ) : (
              // Messages
              <div className="space-y-8 mb-8">
                {messages.map((message) => (
                  <div key={message.id} className="animate-fade-in-up">
                    <div className={cn(
                      "flex gap-6",
                      message.role === "user" ? "flex-row-reverse" : "flex-row"
                    )}>
                      <div className={cn(
                        "flex-shrink-0 w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg",
                        message.role === "user" 
                          ? "bg-gradient-to-br from-primary to-accent" 
                          : "bg-card border-2 border-border"
                      )}>
                        {message.role === "user" ? (
                          <User className="h-5 w-5 text-primary-foreground" />
                        ) : (
                          <Bot className="h-5 w-5 text-muted-foreground" />
                        )}
                      </div>

                      <div className={cn(
                        "flex-1 space-y-2 max-w-[85%]",
                        message.role === "user" ? "items-end" : "items-start"
                      )}>
                        {/* Generating Indicator */}
                        {message.id === generatingMessageId && loadingSystem.isGeneratingVisible && (
                          <div className="mb-2">
                            <GeneratingIndicator
                              isVisible={true}
                              mode={currentRequestMode}
                              messageId={message.id}
                            />
                          </div>
                        )}

                        <Card className={cn(
                          "shadow-lg border-0 backdrop-blur-sm transition-all duration-300 hover:shadow-xl",
                          message.role === "user"
                            ? "bg-gradient-to-r from-primary to-accent text-primary-foreground ml-auto"
                            : "bg-card/90 border border-border"
                        )}>
                          <CardContent className="p-6">
                            <div className={cn(
                              "text-base leading-relaxed",
                              message.role === "user" ? "text-primary-foreground" : "text-foreground",
                              /[\u0980-\u09FF]/.test(message.content) ? 'bangla' : ''
                            )}>
                              {message.content}
                            </div>
                            
                            {message.intent && message.confidence !== undefined && (
                              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border/50">
                                <Badge variant="outline" className="text-xs bg-muted">
                                  {message.intent.charAt(0).toUpperCase() + message.intent.slice(1)} ({(message.confidence * 100).toFixed(0)}%)
                                </Badge>
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  {formatTime(message.timestamp)}
                                </span>
                              </div>
                            )}

                            {message.sources && message.sources.length > 0 && (
                              <div className="mt-4 pt-4 border-t border-border/50">
                                <p className="text-xs text-muted-foreground mb-3 font-medium">তথ্যসূত্র:</p>
                                <div className="flex flex-wrap gap-2">
                                  {message.sources.map((source: any, idx: number) => (
                                    <a
                                      key={idx}
                                      href={source.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1 text-xs bg-muted hover:bg-muted/80 text-muted-foreground px-3 py-1 rounded-full transition-colors"
                                    >
                                      {source.name}
                                      <ExternalLink className="h-3 w-3" />
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-border bg-background/50 backdrop-blur-xl p-6">
          <div className="max-w-4xl mx-auto">
            <Card className="bg-card/90 backdrop-blur-xl border-border shadow-xl">
              <CardContent className="p-6">
                <div className="flex gap-4">
                  <Textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={lang === "bn" ? "আপনার প্রশ্ন লিখুন..." : "Ask your question..."}
                    className={cn(
                      "min-h-[60px] resize-none border-border focus:border-primary text-base bg-background/50 backdrop-blur-sm",
                      lang === "bn" ? "bangla" : ""
                    )}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault()
                        sendMessage()
                      }
                    }}
                    disabled={loadingSystem.state !== 'idle'}
                  />
                  <Button
                    onClick={() => sendMessage()}
                    disabled={!input.trim() || loadingSystem.state !== 'idle'}
                    size="lg"
                    className="px-6 bg-gradient-to-r from-primary to-accent hover:opacity-90 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
                  >
                    <Send className="h-5 w-5" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-3 text-center flex items-center justify-center gap-4">
                  <span className="flex items-center gap-1">
                    <kbd className="px-2 py-1 bg-muted border border-border rounded text-xs font-mono">Enter</kbd>
                    পাঠান
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-2 py-1 bg-muted border border-border rounded text-xs font-mono">Shift+Enter</kbd>
                    নতুন লাইন
                  </span>
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </>
  )
}