"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Send, Bot, User, Newspaper, Sparkles, ChevronRight, Clock, ExternalLink, Loader2 } from "lucide-react"
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

const SAMPLE_QUERIES = [
  { query: "আজকের সর্বশেষ খবর কী?", category: "News", icon: "📰" },
  { query: "বাংলাদেশের আর্থিক অবস্থা", category: "Economy", icon: "💰" },
  { query: "ঢাকার আবহাওয়া কেমন?", category: "Weather", icon: "🌤️" },
  { query: "ক্রিকেট ম্যাচের খবর", category: "Sports", icon: "🏏" },
]

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [lang, setLang] = useState<"bn" | "en">("bn")

  const sendMessage = async (query?: string) => {
    const messageContent = query || input.trim()
    if (!messageContent || isLoading) return

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
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: messageContent, lang })
      })

      if (response.ok) {
        const data = await response.json()
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: data.answer_bn || data.answer_en,
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      {/* Header */}
      <header className="bg-white/90 backdrop-blur-xl border-b border-slate-200/60 sticky top-0 z-50 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <Newspaper className="h-5 w-5 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    KhoborAgent
                  </h1>
                  <p className="text-xs text-slate-500">AI সংবাদ সহায়ক</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="flex items-center bg-slate-100 rounded-xl p-1">
                <Button
                  variant={lang === "bn" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setLang("bn")}
                  className="h-8 px-4 text-xs rounded-lg font-medium"
                >
                  বাংলা
                </Button>
                <Button
                  variant={lang === "en" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setLang("en")}
                  className="h-8 px-4 text-xs rounded-lg font-medium"
                >
                  English
                </Button>
              </div>
              <Badge className="bg-green-100 text-green-700 border-green-200 px-3 py-1 rounded-full">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                অনলাইন
              </Badge>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        {messages.length === 0 && (
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-3xl mb-6 shadow-xl">
              <Sparkles className="h-10 w-10 text-white" />
            </div>
            <h2 className="text-4xl font-bold text-slate-900 mb-4">
              আপনার ব্যক্তিগত সংবাদ সহায়ক
            </h2>
            <p className="text-xl text-slate-600 mb-12 max-w-2xl mx-auto">
              সর্বশেষ সংবাদ, আবহাওয়া, শেয়ার বাজার এবং খেলাধুলার খবর পান আপনার ভাষায়
            </p>
            
            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl mx-auto mb-12">
              {SAMPLE_QUERIES.map((item, index) => (
                <Card 
                  key={index}
                  className="group cursor-pointer border-slate-200 hover:border-blue-300 hover:shadow-xl transition-all duration-300 bg-white/70 backdrop-blur-sm hover:scale-[1.02]"
                  onClick={() => sendMessage(item.query)}
                >
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="text-left">
                        <div className="flex items-center gap-3 mb-3">
                          <span className="text-2xl">{item.icon}</span>
                          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 px-3 py-1">
                            {item.category}
                          </Badge>
                        </div>
                        <p className="text-lg text-slate-700 group-hover:text-slate-900 transition-colors font-medium">
                          {item.query}
                        </p>
                      </div>
                      <ChevronRight className="h-6 w-6 text-slate-400 group-hover:text-blue-600 transition-colors ml-4" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
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
                    ? "bg-gradient-to-br from-blue-600 to-purple-600" 
                    : "bg-white border-2 border-slate-200"
                )}>
                  {message.role === "user" ? (
                    <User className="h-5 w-5 text-white" />
                  ) : (
                    <Bot className="h-5 w-5 text-slate-600" />
                  )}
                </div>

                <div className={cn(
                  "flex-1 space-y-2 max-w-[85%]",
                  message.role === "user" ? "items-end" : "items-start"
                )}>
                  <Card className={cn(
                    "shadow-lg border-0 backdrop-blur-sm transition-all duration-300 hover:shadow-xl",
                    message.role === "user"
                      ? "bg-gradient-to-r from-blue-600 to-purple-600 text-white ml-auto"
                      : "bg-white/90 border border-slate-200"
                  )}>
                    <CardContent className="p-6">
                      <div className={cn(
                        "text-base leading-relaxed",
                        message.role === "user" ? "text-white" : "text-slate-800",
                        /[\u0980-\u09FF]/.test(message.content) ? 'bangla' : ''
                      )}>
                        {message.content}
                      </div>
                      
                      {message.intent && message.confidence !== undefined && (
                        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-200/50">
                          <Badge variant="outline" className="text-xs bg-slate-50">
                            {message.intent.charAt(0).toUpperCase() + message.intent.slice(1)} ({(message.confidence * 100).toFixed(0)}%)
                          </Badge>
                          <span className="text-xs text-slate-500 flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatTime(message.timestamp)}
                          </span>
                        </div>
                      )}

                      {message.sources && message.sources.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-slate-200/50">
                          <p className="text-xs text-slate-500 mb-3 font-medium">তথ্যসূত্র:</p>
                          <div className="flex flex-wrap gap-2">
                            {message.sources.map((source, idx) => (
                              <a
                                key={idx}
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1 rounded-full transition-colors"
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

          {isLoading && (
            <div className="flex gap-6 animate-fade-in-up">
              <div className="flex-shrink-0 w-12 h-12 rounded-2xl bg-white border-2 border-slate-200 flex items-center justify-center shadow-lg">
                <Bot className="h-5 w-5 text-slate-600" />
              </div>
              <Card className="bg-white/90 border border-slate-200 shadow-lg">
                <CardContent className="p-6">
                  <div className="flex items-center gap-3">
                    <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                    <span className="text-slate-600">উত্তর প্রস্তুত করা হচ্ছে...</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        {/* Input */}
        <Card className="sticky bottom-6 bg-white/90 backdrop-blur-xl border-slate-200 shadow-xl">
          <CardContent className="p-6">
            <div className="flex gap-4">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={lang === "bn" ? "আপনার প্রশ্ন লিখুন..." : "Ask your question..."}
                className={cn(
                  "min-h-[60px] resize-none border-slate-200 focus:border-blue-400 text-base bg-white/50 backdrop-blur-sm",
                  lang === "bn" ? "bangla" : ""
                )}
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
                size="lg"
                className="px-6 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </div>
            <p className="text-xs text-slate-500 mt-3 text-center flex items-center justify-center gap-4">
              <span className="flex items-center gap-1">
                <kbd className="px-2 py-1 bg-slate-100 border border-slate-200 rounded text-xs font-mono">Enter</kbd>
                পাঠান
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-2 py-1 bg-slate-100 border border-slate-200 rounded text-xs font-mono">Shift+Enter</kbd>
                নতুন লাইন
              </span>
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}