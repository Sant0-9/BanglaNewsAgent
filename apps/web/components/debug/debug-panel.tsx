"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card"
import { Badge } from "../ui/badge"
import { Button } from "../ui/button"
import { Separator } from "../ui/separator"
import { ScrollArea } from "../ui/scroll-area"
import { Toggle } from "../ui/toggle"
import { 
  Bug, 
  Clock, 
  Database, 
  Zap, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
  Trash2
} from "lucide-react"
import { cn } from "../../lib/utils"

interface DebugEntry {
  id: string
  timestamp: string
  type: 'request' | 'retrieval' | 'gate' | 'error'
  data: {
    query?: string
    intent?: string
    confidence?: number
    sources?: number
    latency?: number
    retrieval_scores?: number[]
    gate_triggered?: string
    error?: string
    [key: string]: any
  }
}

interface DebugPanelProps {
  className?: string
  position?: 'bottom' | 'right'
}

export function DebugPanel({ className, position = 'bottom' }: DebugPanelProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [entries, setEntries] = useState<DebugEntry[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [filter, setFilter] = useState<'all' | 'requests' | 'errors'>('all')

  // Check if we're in development mode
  const isDev = process.env.NODE_ENV === 'development' || 
                process.env.NEXT_PUBLIC_DEBUG === 'true'

  // Don't render in production unless explicitly enabled
  if (!isDev) {
    return null
  }

  // Mock function to simulate receiving debug data
  // In real implementation, this would listen to WebSocket or Server-Sent Events
  useEffect(() => {
    const mockDebugData = () => {
      const mockEntry: DebugEntry = {
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        type: 'request',
        data: {
          query: "আজকের খবর কী?",
          intent: "news",
          confidence: 0.95,
          sources: 5,
          latency: 1200,
          retrieval_scores: [0.89, 0.76, 0.71, 0.68, 0.65],
          gate_triggered: null
        }
      }
      
      setEntries(prev => [...prev, mockEntry].slice(-50)) // Keep last 50 entries
    }

    // Simulate debug entries every 10 seconds in dev mode
    const interval = setInterval(mockDebugData, 10000)
    return () => clearInterval(interval)
  }, [])

  const clearEntries = () => {
    setEntries([])
  }

  const filteredEntries = entries.filter(entry => {
    if (filter === 'requests') return entry.type === 'request'
    if (filter === 'errors') return entry.type === 'error'
    return true
  })

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'request': return <Zap className="w-4 h-4 text-blue-500" />
      case 'retrieval': return <Database className="w-4 h-4 text-green-500" />
      case 'gate': return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />
      default: return <Bug className="w-4 h-4 text-gray-500" />
    }
  }

  const formatLatency = (ms?: number) => {
    if (!ms) return 'N/A'
    return ms < 1000 ? `${ms}ms` : `${(ms/1000).toFixed(2)}s`
  }

  if (!isVisible) {
    return (
      <Button
        onClick={() => setIsVisible(true)}
        size="sm"
        variant="outline"
        className={cn(
          "fixed z-50 bg-background/80 backdrop-blur",
          position === 'bottom' 
            ? "bottom-4 right-4" 
            : "top-20 right-4",
          className
        )}
      >
        <Bug className="w-4 h-4 mr-2" />
        Debug
      </Button>
    )
  }

  return (
    <Card className={cn(
      "fixed z-50 bg-background/95 backdrop-blur border-2",
      position === 'bottom' 
        ? "bottom-4 right-4 w-96 h-80" 
        : "top-20 right-4 w-80 h-96",
      className
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Bug className="w-4 h-4" />
            Debug Panel
            <Badge variant="secondary" className="text-xs">DEV</Badge>
          </CardTitle>
          <div className="flex items-center gap-1">
            <Toggle
              pressed={autoScroll}
              onPressedChange={setAutoScroll}
              size="sm"
              className="h-8"
            >
              {autoScroll ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            </Toggle>
            <Button
              onClick={clearEntries}
              size="sm"
              variant="ghost"
              className="h-8 w-8 p-0"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
            <Button
              onClick={() => setIsVisible(false)}
              size="sm"
              variant="ghost"
              className="h-8 w-8 p-0"
            >
              ✕
            </Button>
          </div>
        </div>
        <div className="flex gap-1">
          <Button
            onClick={() => setFilter('all')}
            size="sm"
            variant={filter === 'all' ? 'default' : 'ghost'}
            className="h-6 text-xs px-2"
          >
            All
          </Button>
          <Button
            onClick={() => setFilter('requests')}
            size="sm"
            variant={filter === 'requests' ? 'default' : 'ghost'}
            className="h-6 text-xs px-2"
          >
            Requests
          </Button>
          <Button
            onClick={() => setFilter('errors')}
            size="sm"
            variant={filter === 'errors' ? 'default' : 'ghost'}
            className="h-6 text-xs px-2"
          >
            Errors
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <ScrollArea className="h-48">
          <div className="space-y-2">
            {filteredEntries.length === 0 ? (
              <div className="text-center text-sm text-muted-foreground py-8">
                No debug entries yet
              </div>
            ) : (
              filteredEntries.map((entry, index) => (
                <div
                  key={entry.id}
                  className="border rounded-lg p-2 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getTypeIcon(entry.type)}
                      <span className="font-medium capitalize">{entry.type}</span>
                    </div>
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Clock className="w-3 h-3" />
                      {formatLatency(entry.data.latency)}
                    </div>
                  </div>
                  
                  {entry.data.query && (
                    <div>
                      <strong>Query:</strong> {entry.data.query.slice(0, 50)}
                      {entry.data.query.length > 50 && '...'}
                    </div>
                  )}
                  
                  <div className="flex flex-wrap gap-1">
                    {entry.data.intent && (
                      <Badge variant="outline" className="text-xs">
                        {entry.data.intent}
                      </Badge>
                    )}
                    {entry.data.confidence && (
                      <Badge variant="outline" className="text-xs">
                        {(entry.data.confidence * 100).toFixed(0)}% conf
                      </Badge>
                    )}
                    {entry.data.sources && (
                      <Badge variant="outline" className="text-xs">
                        {entry.data.sources} sources
                      </Badge>
                    )}
                    {entry.data.gate_triggered && (
                      <Badge variant="destructive" className="text-xs">
                        Gate: {entry.data.gate_triggered}
                      </Badge>
                    )}
                  </div>
                  
                  {entry.data.retrieval_scores && entry.data.retrieval_scores.length > 0 && (
                    <div>
                      <strong>Top Scores:</strong> {
                        entry.data.retrieval_scores
                          .slice(0, 3)
                          .map(s => s.toFixed(2))
                          .join(', ')
                      }
                    </div>
                  )}
                  
                  <div className="text-muted-foreground">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}