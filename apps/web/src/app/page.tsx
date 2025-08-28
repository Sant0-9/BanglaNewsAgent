"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Send, Bot, User, Globe, TrendingUp, Cloud, Trophy, Search } from "lucide-react"
import { cn } from "@/lib/utils"
import { formatTime } from "@/lib/utils"

interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  timestamp: Date
  intent?: string
  confidence?: number
  sources?: Array<{
    name: string
    url: string
  }>
}

const SAMPLE_INTENTS = [
  { icon: Globe, label: "News", query: "Latest news on climate change", color: "bg-blue-500/20 text-blue-400" },
  { icon: Cloud, label: "Weather", query: "What's the weather in Dhaka today?", color: "bg-cyan-500/20 text-cyan-400" },
  { icon: TrendingUp, label: "Markets", query: "AAPL stock price", color: "bg-green-500/20 text-green-400" },
  { icon: Trophy, label: "Sports", query: "Bangladesh cricket score", color: "bg-orange-500/20 text-orange-400" },
  { icon: Search, label: "Lookup", query: "Who is Sundar Pichai?", color: "bg-purple-500/20 text-purple-400" },
]

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([])
  // Add welcome message on client after hydration to avoid SSR mismatch with timestamps
  useEffect(() => {
    setMessages(prev => (
      prev.length > 0
        ? prev
        : [{
            id: "welcome",
            content: "স্বাগতম! আমি KhoborAgent, আপনার সংবাদ সহায়ক। আমি সংবাদ, আবহাওয়া, শেয়ার বাজার, খেলাধুলা এবং সাধারণ তথ্য সম্পর্কে প্রশ্নের উত্তর দিতে পারি।",
            role: "assistant",
            timestamp: new Date(),
            intent: "greeting",
            confidence: 1.0
          }]
    ))
  }, [])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [lang, setLang] = useState<"bn" | "en">("bn")

  const sendMessage = async (query?: string) => {
    const messageContent = query || input.trim()
    if (!messageContent) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: messageContent,
      role: "user",
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      // This would call your actual API
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: messageContent, lang })
      })

      if (response.ok) {
        const data = await response.json()
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: data.answer_bn,
          role: "assistant",
          timestamp: new Date(),
          intent: data.metrics?.intent,
          confidence: data.metrics?.confidence,
          sources: data.sources
        }
        setMessages(prev => [...prev, assistantMessage])
      } else {
        throw new Error("Failed to get response")
      }
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "দুঃখিত, কিছু সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
        role: "assistant",
        timestamp: new Date(),
        intent: "error",
        confidence: 0
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-dark-950 via-dark-900 to-dark-950 overflow-hidden">
      {/* Sidebar */}
      <div className="w-80 border-r border-dark-700/50 bg-dark-950/80 backdrop-blur-xl shadow-2xl">
        <div className="p-6 h-full flex flex-col">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
                <Bot className="h-5 w-5 text-brand-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold gradient-text">
                  KhoborAgent
                </h1>
                <p className="text-xs text-muted-foreground">
                  Smart news & information assistant
                </p>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-hidden">
            <div className="mb-4">
              <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-2">
                <Search className="h-3 w-3" />
                Try These Queries
              </h3>
            </div>
            <div className="space-y-3 overflow-y-auto max-h-[calc(100vh-280px)] pr-2">
            
              {SAMPLE_INTENTS.map((item, index) => (
                <Card 
                  key={index}
                  className="group cursor-pointer border-dark-700/50 bg-dark-900/30 hover:bg-dark-800/60 transition-all duration-300 hover:scale-[1.02] hover:shadow-lg hover:shadow-brand-500/10"
                  onClick={() => sendMessage(item.query)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className={cn("p-2.5 rounded-xl transition-all duration-300 group-hover:scale-110", item.color)}>
                        <item.icon className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <Badge variant="outline" className="text-xs mb-2 border-dark-600">
                          {item.label}
                        </Badge>
                        <p className="text-sm text-muted-foreground line-clamp-2 group-hover:text-foreground transition-colors">
                          {item.query}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-dark-700/50 bg-dark-900/50 backdrop-blur-xl p-4 shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-brand-500/20 border border-brand-500/30 flex items-center justify-center">
                <Bot className="h-4 w-4 text-brand-400" />
              </div>
              <div>
                <h2 className="font-semibold text-foreground">Chat Assistant</h2>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Globe className="h-3 w-3" />
                  News • Weather • Markets • Sports • Lookup
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 bg-dark-800/50 p-1 rounded-lg border border-dark-600">
                <Button
                  variant={lang === "bn" ? "brand" : "ghost"}
                  size="sm"
                  onClick={() => setLang("bn")}
                  className="h-7 px-3 text-xs"
                >
                  বাংলা
                </Button>
                <Button
                  variant={lang === "en" ? "brand" : "ghost"}
                  size="sm"
                  onClick={() => setLang("en")}
                  className="h-7 px-3 text-xs"
                >
                  English
                </Button>
              </div>
              <Badge variant="brand" className="animate-pulse-glow flex items-center gap-1">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                Online
              </Badge>
            </div>
          </div>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 p-6">
          <div className="space-y-8 max-w-4xl mx-auto">
            {messages.map((message) => (
              <div key={message.id} className="animate-fade-in-up">
                <div className={cn(
                  "flex gap-4",
                  message.role === "user" ? "flex-row-reverse" : "flex-row"
                )}>
                  <div className={cn(
                    "flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg",
                    message.role === "user" 
                      ? "bg-brand-600/80 border border-brand-500/30" 
                      : "bg-dark-800/80 border border-dark-600/50 backdrop-blur-sm"
                  )}>
                    {message.role === "user" ? (
                      <User className="h-4 w-4 text-white" />
                    ) : (
                      <Bot className="h-4 w-4 text-brand-400" />
                    )}
                  </div>

                  <div className={cn(
                    "flex-1 space-y-2 max-w-[80%]",
                    message.role === "user" ? "items-end" : "items-start"
                  )}>
                    <Card className={cn(
                      "border shadow-xl backdrop-blur-sm transition-all duration-300 hover:shadow-2xl",
                      message.role === "user"
                        ? "bg-brand-600/20 border-brand-500/30 ml-auto hover:bg-brand-600/30"
                        : "bg-dark-800/60 border-dark-600/50 hover:bg-dark-800/80"
                    )}>
                      <CardContent className="p-5">
                        <div className={`prose-custom text-sm leading-relaxed ${message.content.includes('বাংলা') || /[\u0980-\u09FF]/.test(message.content) ? 'bangla' : ''}`}>
                          {message.content}
                        </div>
                        
                        {message.intent && message.confidence !== undefined && (
                          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-dark-600">
                            <Badge variant="intent" className="text-xs">
                              Routed to: {message.intent.charAt(0).toUpperCase() + message.intent.slice(1)} ({(message.confidence * 100).toFixed(0)}%)
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {formatTime(message.timestamp)}
                            </span>
                          </div>
                        )}

                        {message.sources && message.sources.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-dark-600">
                            <p className="text-xs text-muted-foreground mb-2">Sources:</p>
                            <div className="flex flex-wrap gap-1">
                              {message.sources.map((source, idx) => (
                                <Badge key={idx} variant="outline" className="text-xs">
                                  <a href={source.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                                    {source.name}
                                  </a>
                                </Badge>
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

            {isLoading && (
              <div className="flex gap-3 animate-fade-in-up">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-dark-800 border border-dark-600 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-brand-400 animate-pulse" />
                </div>
                <Card className="bg-dark-800/50 border border-dark-600">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                      <span className="text-sm text-muted-foreground">Processing...</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="border-t border-dark-700/50 bg-dark-900/50 backdrop-blur-xl p-6 shadow-lg">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={lang === "bn" ? "সংবাদ, আবহাওয়া, শেয়ার বাজার, খেলাধুলা বা অন্য কিছু সম্পর্কে জিজ্ঞাসা করুন..." : "Ask me about news, weather, stock prices, sports, or anything else..."}
                className={`min-h-[80px] resize-none bg-dark-800/60 border-dark-600/50 focus:border-brand-500 focus:bg-dark-800/80 transition-all duration-200 ${lang === "bn" ? "bangla" : ""}`}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    sendMessage()
                  }
                }}
                disabled={isLoading}
              />
              <Button
                onClick={() => sendMessage()}
                disabled={!input.trim() || isLoading}
                size="icon"
                variant="brand"
                className="h-20 w-12 shrink-0 shadow-lg hover:shadow-brand-500/25 transition-all duration-200 hover:scale-105"
              >
                <Send className={`h-4 w-4 ${isLoading ? 'animate-pulse' : ''}`} />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-3 text-center flex items-center justify-center gap-2">
              <kbd className="px-2 py-0.5 bg-dark-800 border border-dark-600 rounded text-xs">Enter</kbd>
              to send, 
              <kbd className="px-2 py-0.5 bg-dark-800 border border-dark-600 rounded text-xs">Shift+Enter</kbd>
              for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}