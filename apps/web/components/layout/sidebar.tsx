"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Button } from "../ui/button"
import { Input } from "../ui/input"
import { Badge } from "../ui/badge"
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu"
import { useChat } from "../../contexts/chat-context"
import { getAllRoutes } from "../../lib/routes"
import { cn } from "../../lib/utils"
import { 
  Plus, 
  Search, 
  Newspaper, 
  MoreVertical, 
  Pin, 
  Edit3, 
  Trash2,
  MessageSquare,
  Clock,
  PanelLeftClose,
  PanelLeftOpen
} from "lucide-react"
import { formatDistanceToNow } from "date-fns"

interface SidebarProps {
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

export function Sidebar({ isCollapsed = false, onToggleCollapse }: SidebarProps) {
  const {
    conversations,
    activeConversationId,
    createNewChat,
    switchToChat,
    deleteChat,
    renameChat,
    togglePinChat
  } = useChat()
  
  const [searchQuery, setSearchQuery] = useState("")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState("")
  const pathname = usePathname()
  const routes = getAllRoutes()

  // Filter conversations by search query
  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleCreateNewChat = () => {
    createNewChat()
  }

  const handleRename = (id: string, currentTitle: string) => {
    setEditingId(id)
    setEditTitle(currentTitle)
  }

  const handleSaveRename = (id: string) => {
    if (editTitle.trim()) {
      renameChat(id, editTitle.trim())
    }
    setEditingId(null)
    setEditTitle("")
  }

  const handleCancelRename = () => {
    setEditingId(null)
    setEditTitle("")
  }

  const formatRelativeTime = (date: Date): string => {
    try {
      return formatDistanceToNow(date, { addSuffix: true })
    } catch {
      return 'some time ago'
    }
  }

  return (
    <div className={cn(
      "h-full bg-card flex flex-col transition-all duration-300 ease-in-out",
      isCollapsed ? "w-[60px] border-r border-border" : "w-full"
    )}>
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-xl flex items-center justify-center">
            <Newspaper className="h-4 w-4 text-primary-foreground" />
          </div>
          {!isCollapsed && (
            <>
              <h2 className="font-semibold text-foreground">KhoborAgent</h2>
              <Button
                variant="ghost"
                size="sm"
                className="ml-auto h-8 w-8 p-0 hover:bg-muted"
                onClick={onToggleCollapse}
              >
                <PanelLeftClose className="h-4 w-4" />
              </Button>
            </>
          )}
          {isCollapsed && (
            <Button
              variant="ghost"
              size="sm"
              className="ml-auto h-8 w-8 p-0 hover:bg-muted"
              onClick={onToggleCollapse}
            >
              <PanelLeftOpen className="h-4 w-4" />
            </Button>
          )}
        </div>
        
        {/* New Chat Button */}
        {!isCollapsed ? (
          <Button 
            onClick={handleCreateNewChat}
            className="w-full justify-start gap-2 bg-primary/10 hover:bg-primary/20 text-primary border-primary/20"
            variant="outline"
          >
            <Plus className="h-4 w-4" />
            New Chat
          </Button>
        ) : (
          <Button 
            onClick={handleCreateNewChat}
            className="w-full h-10 p-0 bg-primary/10 hover:bg-primary/20 text-primary border-primary/20"
            variant="outline"
            size="sm"
          >
            <Plus className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Route Navigation */}
      <div className="p-2 border-b border-border">
        {!isCollapsed ? (
          <div className="grid grid-cols-2 gap-1">
            {routes.map((route) => {
              const Icon = route.icon
              const isActive = pathname === route.path
              return (
                <Link key={route.id} href={route.path as any}>
                  <Button
                    variant={isActive ? "default" : "ghost"}
                    size="sm"
                    className={cn(
                      "w-full justify-start gap-2 h-9 text-xs font-medium transition-colors",
                      isActive 
                        ? "bg-primary text-primary-foreground shadow-sm" 
                        : "hover:bg-muted/50 text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {route.title}
                  </Button>
                </Link>
              )
            })}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-1">
            {routes.map((route) => {
              const Icon = route.icon
              const isActive = pathname === route.path
              return (
                <Link key={route.id} href={route.path as any}>
                  <Button
                    variant={isActive ? "default" : "ghost"}
                    size="sm"
                    className={cn(
                      "w-full h-9 p-0 transition-colors",
                      isActive 
                        ? "bg-primary text-primary-foreground shadow-sm" 
                        : "hover:bg-muted/50 text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                  </Button>
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {/* Search */}
      {!isCollapsed && (
        <div className="p-4 border-b border-border">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-background/50 border-border"
            />
          </div>
        </div>
      )}

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto">
        {filteredConversations.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">
            <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
            {!isCollapsed && (
              <>
                <p className="text-sm">
                  {searchQuery ? 'No chats found' : 'No conversations yet'}
                </p>
                {!searchQuery && (
                  <p className="text-xs mt-1">Start a new chat to begin</p>
                )}
              </>
            )}
          </div>
        ) : (
          <div className="p-2">
            {filteredConversations.map((conversation) => (
              <div
                key={conversation.id}
                className={cn(
                  "group relative rounded-lg mb-1 cursor-pointer transition-colors hover:bg-muted/50",
                  conversation.id === activeConversationId && "bg-primary/10 border border-primary/20",
                  isCollapsed ? "p-2" : "p-3"
                )}
                onClick={() => switchToChat(conversation.id)}
              >
                {!isCollapsed ? (
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      {editingId === conversation.id ? (
                        <Input
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onBlur={() => handleSaveRename(conversation.id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveRename(conversation.id)
                            if (e.key === 'Escape') handleCancelRename()
                          }}
                          className="h-6 text-sm px-1 py-0 border-0 bg-background focus:bg-background"
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <div className="flex items-center gap-2">
                          {conversation.isPinned && (
                            <Pin className="h-3 w-3 text-primary flex-shrink-0" />
                          )}
                          <h3 className="font-medium text-sm text-foreground truncate">
                            {conversation.title}
                          </h3>
                        </div>
                      )}
                      
                      <div className="flex items-center gap-2 mt-1">
                        <Clock className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(conversation.updatedAt)}
                        </span>
                        {conversation.messages.length > 0 && (
                          <Badge variant="secondary" className="text-xs px-1.5 py-0">
                            {conversation.messages.length}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Actions Menu */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-muted"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreVertical className="h-3 w-3" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-36">
                        <DropdownMenuItem 
                          onClick={(e) => {
                            e.stopPropagation()
                            togglePinChat(conversation.id)
                          }}
                        >
                          <Pin className="mr-2 h-4 w-4" />
                          {conversation.isPinned ? 'Unpin' : 'Pin'}
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          onClick={(e) => {
                            e.stopPropagation()
                            handleRename(conversation.id, conversation.title)
                          }}
                        >
                          <Edit3 className="mr-2 h-4 w-4" />
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteChat(conversation.id)
                          }}
                          className="text-destructive focus:text-destructive"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                ) : (
                  // Collapsed view - just show a dot indicator
                  <div className="flex items-center justify-center">
                    <div className={cn(
                      "w-2 h-2 rounded-full transition-colors",
                      conversation.id === activeConversationId 
                        ? "bg-primary" 
                        : "bg-muted-foreground"
                    )} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}