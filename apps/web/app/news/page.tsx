"use client"

import { Sidebar } from "../../components/layout/sidebar"
import { RouteChatInterface } from "../../components/chat/route-chat-interface"
import { ChatProvider } from "../../contexts/chat-context"
import { routeConfigs } from "../../lib/routes"
import { useSidebar } from "../../hooks/use-sidebar"
import { ResizablePanels } from "../../components/ui/resizable-panels"

export default function NewsPage() {
  const { isCollapsed, sidebarWidth, toggleSidebar, handleSidebarResize, isLoaded } = useSidebar()

  // Avoid hydration mismatch by not rendering until loaded
  if (!isLoaded) {
    return (
      <div className="h-screen flex bg-background">
        <div className="w-[280px] h-full bg-card border-r border-border animate-pulse" />
        <div className="flex-1" />
      </div>
    )
  }

  return (
    <ChatProvider>
      <div className="h-screen bg-background">
        {!isCollapsed ? (
          <ResizablePanels
            defaultSizePercent={sidebarWidth}
            minSizePercent={15}
            maxSizePercent={40}
            onResize={handleSidebarResize}
            className="h-full"
          >
            <Sidebar 
              isCollapsed={isCollapsed} 
              onToggleCollapse={toggleSidebar}
            />
            <RouteChatInterface routeConfig={routeConfigs.news} />
          </ResizablePanels>
        ) : (
          <div className="h-screen flex">
            <Sidebar 
              isCollapsed={isCollapsed} 
              onToggleCollapse={toggleSidebar}
            />
            <div className="flex-1">
              <RouteChatInterface routeConfig={routeConfigs.news} />
            </div>
          </div>
        )}
      </div>
    </ChatProvider>
  )
}