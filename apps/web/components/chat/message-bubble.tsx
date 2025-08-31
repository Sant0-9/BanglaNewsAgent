"use client"

import { useState } from "react"
import { Button } from "../ui/button"
import { Badge } from "../ui/badge"
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu"
import { Message } from "../../lib/storage"
import { cn } from "../../lib/utils"
import { formatTime } from "../../lib/utils"
import { 
  User, 
  Bot, 
  Copy, 
  RefreshCw, 
  Square, 
  Languages, 
  Expand, 
  Search, 
  Clock,
  ExternalLink,
  MoreHorizontal,
  Check,
  Volume2
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
  onStop?: () => void
  onRegenerate?: () => void
  onCopy?: () => void
  onTranslate?: (targetLang: 'bn' | 'en') => void
  onExpand?: () => void
  onDeepDive?: () => void
  className?: string
}

export function MessageBubble({ 
  message, 
  isStreaming = false,
  onStop,
  onRegenerate,
  onCopy,
  onTranslate,
  onExpand,
  onDeepDive,
  className 
}: MessageBubbleProps) {
  const [showActions, setShowActions] = useState(false)
  const [copied, setCopied] = useState(false)
  const isUser = message.role === "user"
  const isBangla = /[\u0980-\u09FF]/.test(message.content)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    onCopy?.()
  }

  const handleTranslate = (targetLang: 'bn' | 'en') => {
    onTranslate?.(targetLang)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className={cn("group relative", className)}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {isUser ? (
        // User Message (Right-aligned bubble)
        <div className="flex justify-end mb-4">
          <div className="flex items-end gap-2 max-w-[80%]">
            <div className={cn(
              "rounded-2xl rounded-br-md px-4 py-3 shadow-sm",
              "bg-gradient-to-r from-primary to-accent text-primary-foreground",
              "text-base leading-relaxed",
              isBangla ? "bangla" : ""
            )}>
              {message.content}
            </div>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-md">
              <User className="h-4 w-4 text-primary-foreground" />
            </div>
          </div>
        </div>
      ) : (
        // Assistant Message (Left-aligned, no bubble)
        <div className="flex gap-3 mb-6">
          <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center shadow-md flex-shrink-0 mt-1">
            <Bot className="h-4 w-4 text-muted-foreground" />
          </div>
          
          <div className="flex-1 space-y-2">
            {/* Message Content */}
            <div className={cn(
              "text-base leading-relaxed text-foreground prose prose-sm max-w-none",
              isBangla ? "bangla" : ""
            )}>
              {message.content}
              {isStreaming && (
                <motion.span
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                  className="inline-block w-2 h-5 bg-primary ml-1"
                />
              )}
            </div>

            {/* Message Metadata */}
            {(message.intent || message.sources?.length) && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground mt-3">
                {message.intent && message.confidence !== undefined && (
                  <Badge variant="outline" className="text-xs bg-muted/50">
                    {message.intent.charAt(0).toUpperCase() + message.intent.slice(1)} ({(message.confidence * 100).toFixed(0)}%)
                  </Badge>
                )}
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatTime(message.timestamp)}
                </span>
              </div>
            )}

            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-border/50">
                <p className="text-xs text-muted-foreground mb-2 font-medium">তথ্যসূত্র:</p>
                <div className="flex flex-wrap gap-2">
                  {message.sources.map((source, idx) => (
                    <a
                      key={idx}
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs bg-muted/50 hover:bg-muted text-muted-foreground px-2 py-1 rounded-md transition-colors hover:text-foreground"
                    >
                      {source.name}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <AnimatePresence>
              {(showActions || isStreaming) && !isUser && (
                <motion.div
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="flex items-center gap-1 mt-3 pt-2"
                >
                  {isStreaming ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onStop}
                      className="h-7 px-2 text-xs hover:bg-destructive hover:text-destructive-foreground border-destructive/20"
                    >
                      <Square className="h-3 w-3 mr-1" />
                      Stop
                    </Button>
                  ) : (
                    <>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={handleCopy}
                        className="h-7 px-2 text-xs hover:bg-muted"
                      >
                        {copied ? (
                          <>
                            <Check className="h-3 w-3 mr-1" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3 mr-1" />
                            Copy
                          </>
                        )}
                      </Button>
                      
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={onRegenerate}
                        className="h-7 px-2 text-xs hover:bg-muted"
                      >
                        <RefreshCw className="h-3 w-3 mr-1" />
                        Regenerate
                      </Button>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-1 text-xs hover:bg-muted"
                          >
                            <MoreHorizontal className="h-3 w-3" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start" className="w-40">
                          <DropdownMenuItem onClick={() => handleTranslate('bn')}>
                            <Languages className="mr-2 h-4 w-4" />
                            Translate to বাংলা
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleTranslate('en')}>
                            <Languages className="mr-2 h-4 w-4" />
                            Translate to English
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={onExpand}>
                            <Expand className="mr-2 h-4 w-4" />
                            Expand Answer
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={onDeepDive}>
                            <Search className="mr-2 h-4 w-4" />
                            Deep Dive
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      )}
    </motion.div>
  )
}