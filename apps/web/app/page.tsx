"use client"

import { useCallback, useMemo, useRef, useState } from "react"
import { Send, StopCircle, Sparkles, Settings, MessageSquare, Globe, Zap, Moon, Sun } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "../components/ui/button"
import { Textarea } from "../components/ui/textarea"
import { Container } from "../components/container"
import type { AskResponse } from "../lib/types"
import { MessageBubble } from "../components/message-bubble"
import { useAsk } from "../hooks/useAsk"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog"
import { cn } from "../lib/utils"

type ChatMessage = {
  id: string
  role: "user" | "assistant" | "system"
  text?: string
  answer?: AskResponse
  streaming?: boolean
  error?: string
}

type Lang = "bn" | "en"
type Mode = "brief" | "deep"

const SUGGESTED_PROMPTS = [
  { bn: "বাংলাদেশের সর্বশেষ রাজনৈতিক পরিস্থিতি কী?", en: "What's the latest political situation in Bangladesh?" },
  { bn: "আজকের আবহাওয়া কেমন?", en: "What's the weather like today?" },
  { bn: "ক্রিকেট খেলার সর্বশেষ স্কোর জানাও", en: "Tell me the latest cricket scores" },
  { bn: "শেয়ার বাজারের অবস্থা কী?", en: "What's the current stock market condition?" }
]

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [lang, setLang] = useState<Lang>("bn")
  const [mode, setMode] = useState<Mode>("brief")
  const [englishDialogOpen, setEnglishDialogOpen] = useState(false)
  const [englishText, setEnglishText] = useState("")
  const [isDark, setIsDark] = useState(false)

  const currentAssistantIdRef = useRef<string | null>(null)

  const { ask, abort, pending, pendingId, error: askError } = useAsk({
    onChunk: (delta) => {
      const id = currentAssistantIdRef.current
      if (!id || !delta) return
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? {
                ...m,
                streaming: true,
                answer: {
                  answer_bn: (m.answer?.answer_bn || "") + delta,
                  answer_en: m.answer?.answer_en,
                  sources: m.answer?.sources || [],
                  flags: m.answer?.flags || { disagreement: false, single_source: false },
                  metrics:
                    m.answer?.metrics ||
                    { source_count: 0, updated_ct: new Date().toISOString() },
                  followups: m.answer?.followups,
                },
              }
            : m
        )
      )
    },
  })

  const createId = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`)

  const handleSend = useCallback(async () => {
    const query = input.trim()
    if (!query || pendingId) return

    const userId = createId()
    const assistantId = createId()

    // Push user message and placeholder assistant
    setMessages((prev) => [
      ...prev,
      { id: userId, role: "user", text: query },
      { id: assistantId, role: "assistant", streaming: true, answer: {
        answer_bn: "",
        sources: [],
        flags: { disagreement: false, single_source: false },
        metrics: { source_count: 0, updated_ct: new Date().toISOString() },
      }}
    ])

    currentAssistantIdRef.current = assistantId
    setInput("")

    try {
      const data = await ask(query, lang, { mode })
      // Replace placeholder with final answer
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, streaming: false, answer: data } : m)))
    } catch (err) {
      // Mark assistant message as error
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, streaming: false, error: err instanceof Error ? err.message : "Failed" } : m)))
    } finally {
      currentAssistantIdRef.current = null
    }
  }, [input, lang, mode, ask, pendingId])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      } else if (e.key === "Escape") {
        if (pendingId) {
          abort()
          // Annotate current assistant message as cancelled
          const id = currentAssistantIdRef.current
          if (id) {
            setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, streaming: false, error: "Request cancelled" } : m)))
          }
        }
      }
    },
    [handleSend, pendingId, abort]
  )

  const canSend = useMemo(() => input.trim().length > 0 && !pendingId, [input, pendingId])

  const handleSuggestedPrompt = (prompt: string) => {
    setInput(prompt)
    setTimeout(() => {
      handleSend()
    }, 100)
  }

  return (
    <div className={cn(
      "min-h-screen transition-all duration-300 flex flex-col",
      isDark 
        ? "bg-gray-900" 
        : "bg-gradient-to-br from-slate-50 via-white to-blue-50/20"
    )}>
      {/* Modern Header */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          "sticky top-0 z-50 backdrop-blur-xl border-b transition-all duration-300",
          isDark 
            ? "bg-gray-900/80 border-gray-800" 
            : "bg-white/60 border-slate-200/50"
        )}
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo and Title */}
            <motion.div 
              className="flex items-center space-x-3"
              whileHover={{ scale: 1.02 }}
            >
              <div className="relative">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 via-purple-600 to-teal-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
                <motion.div 
                  className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              </div>
              <div>
                <h1 className={cn(
                  "text-xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-teal-600 bg-clip-text text-transparent",
                )}>
                  KhoborAgent
                </h1>
                <p className={cn(
                  "text-xs",
                  isDark ? "text-gray-400" : "text-slate-500"
                )}>
                  Your intelligent Bengali assistant
                </p>
              </div>
            </motion.div>

            {/* Header Actions */}
            <div className="flex items-center space-x-3">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsDark(!isDark)}
                className={cn(
                  "p-2 rounded-xl transition-all duration-200",
                  isDark 
                    ? "text-gray-300 hover:text-white hover:bg-gray-800" 
                    : "text-slate-600 hover:text-slate-800 hover:bg-slate-100"
                )}
              >
                {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </motion.button>
              
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={cn(
                  "p-2 rounded-xl transition-all duration-200",
                  isDark 
                    ? "text-gray-300 hover:text-white hover:bg-gray-800" 
                    : "text-slate-600 hover:text-slate-800 hover:bg-slate-100"
                )}
              >
                <Settings className="w-4 h-4" />
              </motion.button>
            </div>
          </div>
        </div>
      </motion.header>

      {/* Chat Area */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="h-full flex flex-col">
            
            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto py-8 space-y-6">
              <AnimatePresence mode="popLayout">
                {messages.length === 0 ? (
                  <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="text-center py-12"
                  >
                    {/* Welcome Section */}
                    <motion.div
                      initial={{ scale: 0.5, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: 0.2 }}
                      className="mb-8"
                    >
                      <div className="relative mx-auto w-20 h-20 mb-6">
                        <div className="w-20 h-20 bg-gradient-to-br from-blue-500 via-purple-600 to-teal-500 rounded-3xl flex items-center justify-center shadow-2xl">
                          <Sparkles className="w-10 h-10 text-white" />
                        </div>
                        <motion.div 
                          className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full border-3 border-white shadow-lg"
                          animate={{ 
                            scale: [1, 1.2, 1],
                            rotate: [0, 360]
                          }}
                          transition={{ 
                            duration: 3, 
                            repeat: Infinity,
                            ease: "easeInOut" 
                          }}
                        />
                      </div>
                      
                      <h2 className={cn(
                        "text-3xl font-bold mb-3",
                        isDark ? "text-white" : "text-slate-900"
                      )}>
                        Welcome to KhoborAgent
                      </h2>
                      <p className={cn(
                        "text-lg max-w-md mx-auto leading-relaxed",
                        isDark ? "text-gray-300" : "text-slate-600"
                      )}>
                        Your intelligent Bengali AI assistant. Ask anything in Bangla or English for accurate, source-backed answers.
                      </p>
                    </motion.div>

                    {/* Suggested Prompts */}
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 }}
                      className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto"
                    >
                      {SUGGESTED_PROMPTS.map((prompt, index) => (
                        <motion.button
                          key={index}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.5 + index * 0.1 }}
                          whileHover={{ scale: 1.02, y: -2 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => handleSuggestedPrompt(lang === "bn" ? prompt.bn : prompt.en)}
                          className={cn(
                            "p-4 rounded-2xl text-left transition-all duration-200 border",
                            isDark 
                              ? "bg-gray-800/50 hover:bg-gray-800 border-gray-700 text-gray-200" 
                              : "bg-white/70 hover:bg-white border-slate-200/80 text-slate-700 shadow-sm hover:shadow-md"
                          )}
                        >
                          <div className="flex items-start space-x-3">
                            <div className={cn(
                              "w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0",
                              isDark ? "bg-gray-700" : "bg-slate-100"
                            )}>
                              <MessageSquare className="w-4 h-4" />
                            </div>
                            <div className="text-sm">
                              {lang === "bn" ? prompt.bn : prompt.en}
                            </div>
                          </div>
                        </motion.button>
                      ))}
                    </motion.div>
                  </motion.div>
                ) : (
                  <div className="space-y-6">
                    {messages.map((message) => (
                      <motion.div 
                        key={message.id}
                        layout
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        transition={{ duration: 0.3, ease: "easeOut" }}
                      >
                        <MessageBubble
                          role={message.role}
                          userText={message.text}
                          answer={message.answer}
                          streaming={message.streaming}
                          query={message.role === 'assistant' ? messages.find((x, idx) => messages.indexOf(message) > idx && x.role === 'user')?.text : undefined}
                          onAction={async (action) => {
                            if (message.role !== 'assistant') return
                            const lastUser = [...messages].reverse().find((x) => x.role === 'user')
                            const query = lastUser?.text || ''

                            switch (action.type) {
                              case 'deep': {
                                setInput(query)
                                setMode('deep')
                                await handleSend()
                                break
                              }
                              case 'related': {
                                if (typeof action.payload === 'string') {
                                  setInput(action.payload)
                                  await handleSend()
                                }
                                break
                              }
                              case 'english': {
                                if (message.answer && message.answer.answer_en) {
                                  setEnglishText(message.answer.answer_en)
                                  setEnglishDialogOpen(true)
                                } else {
                                  if (pendingId) return
                                  
                                  const userId = createId()
                                  const assistantId = createId()
                                  setMessages((prev): ChatMessage[] => [
                                    ...prev,
                                    { id: userId, role: 'user', text: query + ' (English)' },
                                    { id: assistantId, role: 'assistant', streaming: true, answer: { answer_bn: '', answer_en: undefined, sources: [], flags: { disagreement: false, single_source: false }, metrics: { source_count: 0, updated_ct: new Date().toISOString() }, followups: [] } },
                                  ])
                                  currentAssistantIdRef.current = assistantId
                                  try {
                                    const data = await ask(query, 'en', { mode })
                                    setMessages((prev) => prev.map((mm) => (mm.id === assistantId ? { ...mm, streaming: false, answer: data } : mm)))
                                  } catch (err) {
                                    setMessages((prev) => prev.map((mm) => (mm.id === assistantId ? { ...mm, streaming: false, error: err instanceof Error ? err.message : 'Failed' } : mm)))
                                  } finally {
                                    currentAssistantIdRef.current = null
                                  }
                                }
                                break
                              }
                            }
                          }}
                        />
                      </motion.div>
                    ))}
                  </div>
                )}
              </AnimatePresence>
            </div>

            {/* Input Area */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="sticky bottom-0 pb-8"
            >
              <div className={cn(
                "relative rounded-3xl border shadow-lg transition-all duration-300",
                isDark 
                  ? "bg-gray-800/90 border-gray-700 shadow-gray-900/20" 
                  : "bg-white/90 border-slate-200/80 shadow-slate-900/10"
              )}>
                <div className="p-4">
                  {/* Input */}
                  <div className="flex items-end space-x-4">
                    <div className="flex-1">
                      <Textarea
                        placeholder={lang === "bn" ? "আমাকে কিছু জিজ্ঞাসা করুন..." : "Ask me anything..."}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        className={cn(
                          "min-h-[52px] max-h-[200px] border-0 bg-transparent resize-none focus:ring-0 placeholder:transition-colors",
                          isDark 
                            ? "text-white placeholder:text-gray-400" 
                            : "text-slate-900 placeholder:text-slate-500"
                        )}
                        disabled={!!pendingId}
                      />
                    </div>

                    {/* Send Button */}
                    <motion.div 
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <Button 
                        onClick={handleSend} 
                        disabled={!canSend}
                        className={cn(
                          "w-12 h-12 rounded-2xl p-0 transition-all duration-200 shadow-lg disabled:opacity-50",
                          canSend
                            ? "bg-gradient-to-r from-blue-600 via-purple-600 to-teal-600 hover:from-blue-700 hover:via-purple-700 hover:to-teal-700 text-white shadow-blue-500/25"
                            : "bg-gray-200 text-gray-400"
                        )}
                      >
                        {pendingId ? (
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                          >
                            <StopCircle className="w-5 h-5" />
                          </motion.div>
                        ) : (
                          <Send className="w-5 h-5" />
                        )}
                      </Button>
                    </motion.div>
                  </div>

                  {/* Controls Row */}
                  <div className="flex items-center justify-between mt-3">
                    <div className="flex items-center space-x-2">
                      {/* Language Toggle */}
                      <div className={cn(
                        "flex rounded-xl p-1 transition-all duration-200",
                        isDark ? "bg-gray-700/70" : "bg-slate-100/80"
                      )}>
                        <button
                          className={cn(
                            "px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200",
                            lang === "bn" 
                              ? "bg-white text-blue-600 shadow-sm dark:bg-gray-600 dark:text-blue-400" 
                              : cn(
                                  "hover:bg-white/50",
                                  isDark ? "text-gray-300 hover:text-white" : "text-slate-600 hover:text-slate-800"
                                )
                          )}
                          onClick={() => setLang("bn")}
                        >
                          বাংলা
                        </button>
                        <button
                          className={cn(
                            "px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200",
                            lang === "en" 
                              ? "bg-white text-blue-600 shadow-sm dark:bg-gray-600 dark:text-blue-400" 
                              : cn(
                                  "hover:bg-white/50",
                                  isDark ? "text-gray-300 hover:text-white" : "text-slate-600 hover:text-slate-800"
                                )
                          )}
                          onClick={() => setLang("en")}
                        >
                          English
                        </button>
                      </div>

                      {/* Mode Toggle */}
                      <div className={cn(
                        "flex rounded-xl p-1 transition-all duration-200",
                        isDark ? "bg-gray-700/70" : "bg-slate-100/80"
                      )}>
                        <button
                          className={cn(
                            "px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200",
                            mode === "brief" 
                              ? "bg-white text-purple-600 shadow-sm dark:bg-gray-600 dark:text-purple-400" 
                              : cn(
                                  "hover:bg-white/50",
                                  isDark ? "text-gray-300 hover:text-white" : "text-slate-600 hover:text-slate-800"
                                )
                          )}
                          onClick={() => setMode("brief")}
                        >
                          Brief
                        </button>
                        <button
                          className={cn(
                            "px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200",
                            mode === "deep" 
                              ? "bg-white text-purple-600 shadow-sm dark:bg-gray-600 dark:text-purple-400" 
                              : cn(
                                  "hover:bg-white/50",
                                  isDark ? "text-gray-300 hover:text-white" : "text-slate-600 hover:text-slate-800"
                                )
                          )}
                          onClick={() => setMode("deep")}
                        >
                          Deep
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {askError && (
                        <motion.span 
                          initial={{ opacity: 0, x: 10 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="text-xs text-red-500"
                        >
                          {askError}
                        </motion.span>
                      )}
                      <span className={cn(
                        "text-xs transition-colors",
                        isDark ? "text-gray-400" : "text-slate-500"
                      )}>
                        {lang === "bn" ? "এন্টার চেপে পাঠান" : "Press Enter to send"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* English Answer Dialog */}
      <Dialog open={englishDialogOpen} onOpenChange={setEnglishDialogOpen}>
        <DialogContent className={cn(
          "max-w-2xl max-h-[80vh] overflow-y-auto rounded-3xl border-0 shadow-2xl",
          isDark ? "bg-gray-800 text-white" : "bg-white"
        )}>
          <DialogHeader>
            <DialogTitle className={cn(
              "text-lg font-semibold",
              isDark ? "text-white" : "text-slate-900"
            )}>
              English Translation
            </DialogTitle>
          </DialogHeader>
          <div className={cn(
            "prose prose-sm max-w-none",
            isDark ? "prose-invert" : "prose-slate"
          )}>
            {englishText}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}