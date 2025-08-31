"use client"

import { Sidebar } from "../../components/layout/sidebar"
import { RouteChatInterface } from "../../components/chat/route-chat-interface"
import { ChatProvider } from "../../contexts/chat-context"
import { routeConfigs } from "../../lib/routes"

export default function WeatherPage() {
  return (
    <ChatProvider>
      <div className="h-screen flex bg-background">
        <Sidebar />
        <RouteChatInterface routeConfig={routeConfigs.weather} />
      </div>
    </ChatProvider>
  )
}