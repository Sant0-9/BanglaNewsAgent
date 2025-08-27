"use client"

import { useCallback, useMemo, useRef, useState } from "react"
import { Send, StopCircle } from "lucide-react"
import { Button } from "../components/ui/button"
import { Textarea } from "../components/ui/textarea"
import { Container } from "../components/container"
import type { AskResponse } from "../lib/types"
import { MessageBubble } from "../components/message-bubble"
import { useAsk } from "../hooks/useAsk"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog"

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

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [lang, setLang] = useState<Lang>("bn")
  const [mode, setMode] = useState<Mode>("brief")
  const [englishDialogOpen, setEnglishDialogOpen] = useState(false)
  const [englishText, setEnglishText] = useState("")

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

  return (
    <>
    <div className="flex flex-col h-[100dvh]">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto">
        <Container size="md" className="max-w-3xl py-6">
          <div className="space-y-4">
            {messages.map((m) => (
              <div key={m.id} className="flex">
                <MessageBubble
                  role={m.role}
                  userText={m.text}
                  answer={m.answer}
                  streaming={m.streaming}
                  query={m.role === 'assistant' ? messages.find((x, idx) => messages.indexOf(m) > idx && x.role === 'user')?.text : undefined}
                  onAction={async (action) => {
                    if (m.role !== 'assistant') return
                    const lastUser = [...messages].reverse().find((x) => x.role === 'user')
                    const query = lastUser?.text || ''

                    switch (action.type) {
                      case 'deep': {
                        // Resubmit the same query with deep mode
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
                        // If we already have english answer, show it directly without creating new messages
                        if (m.answer && m.answer.answer_en) {
                          setEnglishText(m.answer.answer_en)
                          setEnglishDialogOpen(true)
                        } else {
                          // Only re-ask in English if answer_en is missing and we're not already streaming
                          if (pendingId) return // Prevent new request while streaming
                          
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
              </div>
            ))}
          </div>
        </Container>
      </div>

      {/* Composer */}
      <div className="sticky bottom-0 border-t bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <Container size="md" className="max-w-3xl">
          <div className="py-3">
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <Textarea
                  placeholder="Type your message..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="min-h-[64px] max-h-[40vh] resize-y"
                  disabled={!!pendingId}
                />
                <div className="mt-1 flex items-center justify-between">
                  <p className="text-[11px] text-muted-foreground">Enter to send · Shift+Enter for newline · Esc to cancel</p>
                  {askError && <p className="text-[11px] text-red-500">{askError}</p>}
                </div>
              </div>

              <div className="flex flex-col gap-2 w-[220px]">
                <div className="flex rounded-md border p-1 bg-background">
                  <Button
                    type="button"
                    size="sm"
                    variant={lang === "bn" ? "brand" : "outline"}
                    className="flex-1"
                    onClick={() => setLang("bn")}
                  >
                    Bangla
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={lang === "en" ? "brand" : "outline"}
                    className="flex-1"
                    onClick={() => setLang("en")}
                  >
                    English
                  </Button>
                </div>
                <div className="flex rounded-md border p-1 bg-background">
                  <Button
                    type="button"
                    size="sm"
                    variant={mode === "brief" ? "brand" : "outline"}
                    className="flex-1"
                    onClick={() => setMode("brief")}
                  >
                    Brief
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={mode === "deep" ? "brand" : "outline"}
                    className="flex-1"
                    onClick={() => setMode("deep")}
                  >
                    Deep
                  </Button>
                </div>
              </div>

              <div className="flex flex-col gap-2 w-[96px]">
                <Button type="button" onClick={handleSend} disabled={!canSend} className="w-full" variant="brand">
                  <Send className="h-4 w-4 mr-1" /> Send
                </Button>
                <Button type="button" onClick={() => abort()} disabled={!pendingId} variant="outline" className="w-full">
                  <StopCircle className="h-4 w-4 mr-1" /> Cancel
                </Button>
              </div>
            </div>
          </div>
        </Container>
      </div>
    </div>

    {/* English Answer Dialog */}
    <Dialog open={englishDialogOpen} onOpenChange={setEnglishDialogOpen}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>English Answer</DialogTitle>
        </DialogHeader>
        <div className="prose prose-sm max-w-none whitespace-pre-wrap">
          {englishText}
        </div>
      </DialogContent>
    </Dialog>
    </>
  )
}