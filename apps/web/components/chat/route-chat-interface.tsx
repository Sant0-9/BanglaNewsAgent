"use client"

import { useState, useRef, useCallback } from "react"
import { Button } from "../ui/button"
import { Card, CardContent } from "../ui/card"
import { Badge } from "../ui/badge"
import { Textarea } from "../ui/textarea"
import { ThemeToggle } from "../ui/theme-toggle"
import { MessageBubble } from "./message-bubble"
import { useStreamingResponse } from "./streaming-message"
import { useChat } from "../../contexts/chat-context"
import { getRouteConfig, type RouteConfig } from "../../lib/routes"
import { cn } from "../../lib/utils"
import { 
  Send, 
  Loader2,
  Sparkles
} from "lucide-react"

interface RouteChatInterfaceProps {
  routeConfig: RouteConfig
}

export function RouteChatInterface({ routeConfig }: RouteChatInterfaceProps) {
  const { 
    activeConversation, 
    addMessage, 
    currentMode, 
    conversationLanguage, 
    setConversationLanguage 
  } = useChat()
  const [input, setInput] = useState("")
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { isStreaming, content, error, startStream, stopStream } = useStreamingResponse()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const sendMessage = async (query?: string) => {
    const messageContent = query || input.trim()
    if (!messageContent || isStreaming) return

    const userMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substring(7)}`,
      content: messageContent,
      role: "user" as const,
      timestamp: new Date()
    }

    // Add user message immediately
    addMessage(userMessage)
    setInput("")

    // Create streaming message ID
    const streamingId = `msg_${Date.now() + 1}_${Math.random().toString(36).substring(7)}`
    setStreamingMessageId(streamingId)

    // Start streaming
    const finalContent = await startStream(messageContent, {
      // Do not pass UI route mode to backend; it only supports content lang.
      lang: conversationLanguage
    })

    // Add final message to conversation
    if (finalContent) {
      const assistantMessage = {
        id: streamingId,
        content: finalContent,
        role: "assistant" as const,
        timestamp: new Date(),
        intent: "response",
        confidence: 0.9
      }
      addMessage(assistantMessage)
    } else if (error) {
      // Show a helpful error message instead of disappearing
      addMessage({
        id: streamingId,
        content: error || (conversationLanguage === 'bn' ? 'দুঃখিত, কিছু সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।' : 'Sorry, something went wrong. Please try again.'),
        role: 'assistant',
        timestamp: new Date(),
        intent: 'error',
        confidence: 0
      })
    }

    setStreamingMessageId(null)
    setTimeout(scrollToBottom, 100)
  }

  const handleStop = () => {
    stopStream()
    setStreamingMessageId(null)
  }

  const handleRegenerate = useCallback((messageId: string) => {
    // Find the message and its preceding user message
    const messages = activeConversation?.messages || []
    const messageIndex = messages.findIndex(m => m.id === messageId)
    if (messageIndex > 0) {
      const userMessage = messages[messageIndex - 1]
      if (userMessage.role === 'user') {
        sendMessage(userMessage.content)
      }
    }
  }, [activeConversation?.messages])

  const handleCopy = useCallback(() => {
    // Copy action feedback is handled in MessageBubble
  }, [])

  const handleTranslate = useCallback((targetLang: 'bn' | 'en') => {
    // TODO: Implement translation functionality
    console.log('Translate to:', targetLang)
  }, [])

  const handleExpand = useCallback(() => {
    // TODO: Implement expand functionality
    console.log('Expand answer')
  }, [])

  const handleDeepDive = useCallback(() => {
    // TODO: Implement deep dive functionality
    console.log('Deep dive')
  }, [])

  const messages = activeConversation?.messages || []

  return (
    <div className="flex-1 flex flex-col h-screen">
      {/* Sticky Header */}
      <header className="bg-card/80 backdrop-blur-xl border-b border-border sticky top-0 z-40 shadow-sm shrink-0">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-xl flex items-center justify-center">
                <routeConfig.icon className="h-4 w-4 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                  KhoborAgent
                </h1>
                <p className="text-xs text-muted-foreground">{routeConfig.title} Mode</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="flex items-center bg-muted rounded-xl p-1">
                <Button
                  variant={conversationLanguage === "bn" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setConversationLanguage("bn")}
                  className="h-8 px-4 text-xs rounded-lg font-medium"
                >
                  বাংলা
                </Button>
                <Button
                  variant={conversationLanguage === "en" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setConversationLanguage("en")}
                  className="h-8 px-4 text-xs rounded-lg font-medium"
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

      {/* Chat Content - Full Height with Independent Scroll */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-4xl mx-auto px-6 h-full">
          {/* Route Banner */}
          <div className={cn(
            "relative overflow-hidden rounded-2xl mb-8 mt-6",
            `bg-gradient-to-r ${routeConfig.banner.gradient}`
          )}>
            <div className="relative p-8 text-white">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h2 className="text-3xl font-bold mb-2">
                    {routeConfig.banner.title}
                  </h2>
                  <p className="text-lg opacity-90 max-w-2xl">
                    {routeConfig.banner.description}
                  </p>
                </div>
                <div className="text-6xl opacity-20 ml-8">
                  {routeConfig.banner.bgIcon}
                </div>
              </div>
            </div>
          </div>

          {/* Welcome Section or Messages */}
          {messages.length === 0 ? (
            <div className="text-center mb-12">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary to-accent rounded-2xl mb-6 shadow-xl">
                <Sparkles className="h-8 w-8 text-primary-foreground" />
              </div>
              <h3 className="text-2xl font-bold text-foreground mb-4">
                এই বিষয়ে আমাকে প্রশ্ন করুন
              </h3>
              
              {/* Quick Prompts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-4xl mx-auto mb-8">
                {routeConfig.quickPrompts.map((prompt, index) => (
                  <Card 
                    key={index}
                    className="group cursor-pointer border-border hover:border-primary/50 hover:shadow-lg transition-all duration-300 bg-card/50 backdrop-blur-sm hover:scale-[1.02]"
                    onClick={() => sendMessage(prompt.text)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <span className="text-xl flex-shrink-0">{prompt.icon}</span>
                        <div className="flex-1 text-left">
                          <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 mb-2 text-xs">
                            {prompt.category}
                          </Badge>
                          <p className="text-sm text-foreground group-hover:text-primary transition-colors font-medium">
                            {prompt.text}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ) : (
            // Messages
            <div className="py-8 space-y-4 min-h-full">
              {messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  onRegenerate={() => handleRegenerate(message.id)}
                  onCopy={handleCopy}
                  onTranslate={handleTranslate}
                  onExpand={handleExpand}
                  onDeepDive={handleDeepDive}
                />
              ))}

              {/* Streaming Message */}
              {isStreaming && streamingMessageId && (
                <MessageBubble
                  message={{
                    id: streamingMessageId,
                    content,
                    role: "assistant",
                    timestamp: new Date()
                  }}
                  isStreaming={true}
                  onStop={handleStop}
                />
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Sticky Input Footer */}
      <div className="sticky bottom-0 border-t border-border bg-background/95 backdrop-blur-xl p-6 shrink-0 z-30">
        <div className="max-w-4xl mx-auto">
          <Card className="bg-card/90 backdrop-blur-xl border-border shadow-2xl">
            <CardContent className="p-6">
              <div className="flex gap-4">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={conversationLanguage === "bn" ? "আপনার প্রশ্ন লিখুন..." : "Ask your question..."}
                  className={cn(
                    "min-h-[60px] max-h-[120px] resize-none border-border focus:border-primary text-base bg-background/50 backdrop-blur-sm",
                    conversationLanguage === "bn" ? "bangla" : ""
                  )}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      sendMessage()
                    }
                  }}
                  disabled={isStreaming}
                />
                <Button
                  onClick={() => sendMessage()}
                  disabled={!input.trim() || isStreaming}
                  size="lg"
                  className="px-6 bg-gradient-to-r from-primary to-accent hover:opacity-90 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105 self-end"
                >
                  {isStreaming ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
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
  )
}