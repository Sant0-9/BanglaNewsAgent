"use client"

import { Sidebar } from "@/components/layout/sidebar"
import { ChatInterface } from "@/components/chat/chat-interface"
import { ChatProvider } from "@/contexts/chat-context"

export default function HomePage() {
  return (
    <ChatProvider>
      <div className="h-screen flex bg-background">
        <Sidebar />
        <ChatInterface />
      </div>
    </ChatProvider>
  )
}