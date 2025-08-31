"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card"
import { Button } from "../ui/button"
import { Badge } from "../ui/badge"
import { CitationSystem } from "./citation-system"
import { InlineMarker } from "./inline-marker"
import { ConfidenceIndicator } from "./confidence-indicator"
import { cn } from "../../lib/utils"
import { 
  Bot, 
  User, 
  RotateCcw, 
  Eye,
  EyeOff,
  Settings
} from "lucide-react"
import type { Source } from "../../lib/types"

const DEMO_SOURCES: Source[] = [
  {
    name: "BBC News - Climate Change Report",
    url: "https://www.bbc.com/news/climate-change-report-2024",
    published_at: "2024-01-15T10:30:00Z",
    logo: "https://logo.clearbit.com/bbc.com"
  },
  {
    name: "Reuters - Economic Analysis", 
    url: "https://www.reuters.com/markets/economic-analysis-2024",
    published_at: "2024-01-14T15:45:00Z"
  },
  {
    name: "The Guardian - Environmental Study",
    url: "https://www.theguardian.com/environment/2024/jan/13/study-findings",
    published_at: "2024-01-13T08:20:00Z",
    logo: "https://logo.clearbit.com/theguardian.com"
  },
  {
    name: "Nature Journal - Scientific Research",
    url: "https://www.nature.com/articles/research-paper-2024",
    published_at: "2024-01-12T12:15:00Z"
  }
]

const DEMO_MESSAGES = [
  {
    content: "Climate change continues to be one of the most pressing global challenges of our time. Recent scientific studies have shown alarming trends in global temperature rise and sea level increases. The latest IPCC report highlights the urgent need for immediate action to reduce greenhouse gas emissions. Many countries are now implementing renewable energy policies to combat these environmental challenges.",
    confidence: 0.85,
    sources: DEMO_SOURCES
  },
  {
    content: "The economic impact of climate policies varies significantly across different regions. While some argue that environmental regulations may slow economic growth, recent data suggests that green investments actually create more jobs than traditional industries. The transition to renewable energy has proven to be both environmentally beneficial and economically viable in many developed countries.",
    confidence: 0.45,
    sources: DEMO_SOURCES.slice(0, 2)
  },
  {
    content: "Artificial intelligence and machine learning technologies are increasingly being used to address environmental challenges. These technologies can optimize energy consumption, predict weather patterns, and improve resource management. However, the energy consumption of AI systems themselves remains a concern that researchers are actively working to address.",
    confidence: 0.72,
    sources: DEMO_SOURCES.slice(1, 4)
  }
]

export function CitationDemo() {
  const [selectedMessage, setSelectedMessage] = useState(0)
  const [showSourcesExpanded, setShowSourcesExpanded] = useState(false)
  const [showConfidenceAlways, setShowConfidenceAlways] = useState(false)
  const [enableKeyboardNav, setEnableKeyboardNav] = useState(true)

  const currentMessage = DEMO_MESSAGES[selectedMessage]

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            Citation System Demo
          </h1>
          <p className="text-muted-foreground text-lg max-w-3xl mx-auto">
            Interactive demonstration of the new inline citation system with markers, sources tray, and accessibility features.
          </p>
        </div>

        {/* Controls */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Demo Controls
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Message Selection */}
            <div>
              <h3 className="text-sm font-medium mb-3">Sample Messages</h3>
              <div className="flex flex-wrap gap-2">
                {DEMO_MESSAGES.map((msg, index) => (
                  <Button
                    key={index}
                    variant={selectedMessage === index ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedMessage(index)}
                    className="h-auto p-3 text-left"
                  >
                    <div>
                      <div className="font-medium mb-1">
                        Message {index + 1}
                      </div>
                      <div className="text-xs opacity-70">
                        {msg.sources.length} sources, {Math.round(msg.confidence * 100)}% confidence
                      </div>
                    </div>
                  </Button>
                ))}
              </div>
            </div>

            {/* Options */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div>
                  <h4 className="font-medium text-sm">Sources Expanded</h4>
                  <p className="text-xs text-muted-foreground">Start with tray open</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowSourcesExpanded(!showSourcesExpanded)}
                >
                  {showSourcesExpanded ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                </Button>
              </div>

              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div>
                  <h4 className="font-medium text-sm">Show All Confidence</h4>
                  <p className="text-xs text-muted-foreground">Show even high confidence</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowConfidenceAlways(!showConfidenceAlways)}
                >
                  {showConfidenceAlways ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                </Button>
              </div>

              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div>
                  <h4 className="font-medium text-sm">Keyboard Navigation</h4>
                  <p className="text-xs text-muted-foreground">Enable [ ] keys</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEnableKeyboardNav(!enableKeyboardNav)}
                >
                  {enableKeyboardNav ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Main Demo */}
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Chat Message Preview */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Message with Citations</CardTitle>
              </CardHeader>
              <CardContent>
                {/* Simulated Chat Message */}
                <div className="flex gap-4 mb-6">
                  <div className="flex-shrink-0 w-12 h-12 rounded-2xl bg-card border-2 border-border flex items-center justify-center shadow-lg">
                    <Bot className="h-5 w-5 text-muted-foreground" />
                  </div>

                  <Card className="flex-1 bg-card/90 border border-border shadow-lg">
                    <CardContent className="p-6">
                      <CitationSystem
                        content={currentMessage.content}
                        sources={currentMessage.sources}
                        confidence={currentMessage.confidence}
                        messageId={`demo-message-${selectedMessage}`}
                        showConfidenceAlways={showConfidenceAlways}
                        defaultSourcesExpanded={showSourcesExpanded}
                        enableKeyboardNavigation={enableKeyboardNav}
                      />
                    </CardContent>
                  </Card>
                </div>

                {/* Instructions */}
                <div className="p-4 bg-fire-ember/10 border border-fire-ember/20 rounded-lg">
                  <h4 className="font-medium text-fire-ember mb-2">
                    🎮 Interactive Demo
                  </h4>
                  <div className="text-sm text-fire-ember space-y-1">
                    <p>• Click on numeric markers ① ② ③ to highlight corresponding sources</p>
                    <p>• Use <kbd className="bg-fire-ember/20 px-1 rounded">[</kbd> and <kbd className="bg-fire-ember/20 px-1 rounded">]</kbd> keys to navigate between markers</p>
                    <p>• Click on sources in the tray to highlight markers</p>
                    <p>• Expand/collapse the Sources section</p>
                    <p>• External links open in new tabs</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Components Showcase */}
          <div className="space-y-6">
            {/* Inline Markers */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Inline Markers</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <h4 className="text-sm font-medium mb-2">Normal State</h4>
                  <div className="flex gap-2 flex-wrap">
                    {[1, 2, 3, 5, 10, 15, 25].map(num => (
                      <InlineMarker key={num} number={num} />
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-2">Highlighted State</h4>
                  <div className="flex gap-2 flex-wrap">
                    {[1, 2, 3].map(num => (
                      <InlineMarker key={num} number={num} isHighlighted />
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Confidence Indicators */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Confidence Indicators</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <h4 className="text-sm font-medium mb-2">Different Levels</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <ConfidenceIndicator confidence={0.2} showAlways />
                      <span className="text-xs text-muted-foreground">Very Low (20%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <ConfidenceIndicator confidence={0.45} showAlways />
                      <span className="text-xs text-muted-foreground">Low (45%)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <ConfidenceIndicator confidence={0.75} showAlways />
                      <span className="text-xs text-muted-foreground">High (75%) - normally hidden</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Features */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Features</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>Inline numeric markers ① ② ③</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>Collapsible sources tray</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>Click-to-highlight mapping</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>Keyboard navigation [ ]</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>Mobile responsive design</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>Accessibility features</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>Low confidence indicators</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>URL truncation with hover</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Technical Details */}
        <Card>
          <CardHeader>
            <CardTitle>Implementation Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium mb-3">Before (Citation Bubbles)</h4>
                <div className="p-4 bg-muted/50 rounded-lg">
                  <div className="text-sm text-muted-foreground space-y-2">
                    <p>❌ Large hover tooltips with source details</p>
                    <p>❌ Giant blocks that interrupted reading flow</p>
                    <p>❌ No keyboard navigation support</p>
                    <p>❌ Mobile unfriendly hover interactions</p>
                    <p>❌ Poor accessibility for screen readers</p>
                  </div>
                </div>
              </div>
              <div>
                <h4 className="font-medium mb-3">After (Inline Citations)</h4>
                <div className="p-4 bg-green-500/10 rounded-lg">
                  <div className="text-sm text-green-700 dark:text-green-400 space-y-2">
                    <p>✅ Compact numeric markers ① ② ③</p>
                    <p>✅ Clean, collapsible sources tray</p>
                    <p>✅ Keyboard navigation with [ ] keys</p>
                    <p>✅ Mobile-first responsive design</p>
                    <p>✅ Full ARIA labels and screen reader support</p>
                    <p>✅ Click-to-highlight source mapping</p>
                    <p>✅ Confidence indicators for reliability</p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}