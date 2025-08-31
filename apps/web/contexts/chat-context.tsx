"use client"

import { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { usePathname } from "next/navigation"
import { storage, Conversation, Message } from "../lib/storage"
import { getRouteConfig } from "../lib/routes"

interface ChatContextType {
  conversations: Conversation[]
  activeConversationId: string | null
  activeConversation: Conversation | null
  currentMode: string
  isLoading: boolean
  conversationLanguage: 'bn' | 'en'
  
  // Actions
  createNewChat: () => string
  switchToChat: (id: string) => void
  deleteChat: (id: string) => void
  renameChat: (id: string, newTitle: string) => void
  togglePinChat: (id: string) => void
  addMessage: (message: Message) => void
  refreshConversations: () => void
  setMode: (mode: string) => void
  toggleConversationLanguage: () => Promise<void>
  setConversationLanguage: (lang: 'bn' | 'en') => Promise<void>
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export function ChatProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [currentMode, setCurrentMode] = useState<string>('home')
  const [isLoading, setIsLoading] = useState(true)
  const [conversationLanguage, setConversationLanguageState] = useState<'bn' | 'en'>('bn')
  const pathname = usePathname()

  // Get active conversation
  const activeConversation = conversations.find(conv => conv.id === activeConversationId) || null

  // Update mode based on current path
  useEffect(() => {
    const routeConfig = getRouteConfig(pathname)
    setCurrentMode(routeConfig.id)
  }, [pathname])

  // Load conversations from storage on mount
  useEffect(() => {
    const loadConversations = () => {
      const storedConversations = storage.getConversationsSorted()
      setConversations(storedConversations)
      
      const activeId = storage.getActiveChat()
      if (activeId && storedConversations.find(conv => conv.id === activeId)) {
        setActiveConversationId(activeId)
      } else if (storedConversations.length > 0) {
        // If no valid active chat, use the first one
        setActiveConversationId(storedConversations[0].id)
        storage.setActiveChat(storedConversations[0].id)
      }
      
      setIsLoading(false)
    }

    loadConversations()
  }, [])

  const refreshConversations = () => {
    const storedConversations = storage.getConversationsSorted()
    setConversations(storedConversations)
  }

  const createNewChat = (): string => {
    const newConversation = storage.createConversation()
    setActiveConversationId(newConversation.id)
    refreshConversations()
    return newConversation.id
  }

  const switchToChat = (id: string) => {
    setActiveConversationId(id)
    storage.setActiveChat(id)
  }

  const deleteChat = (id: string) => {
    const wasActive = id === activeConversationId
    storage.deleteConversation(id)
    
    refreshConversations()
    
    if (wasActive) {
      const remainingConversations = storage.getConversationsSorted()
      if (remainingConversations.length > 0) {
        setActiveConversationId(remainingConversations[0].id)
        storage.setActiveChat(remainingConversations[0].id)
      } else {
        setActiveConversationId(null)
        storage.clearActiveChat()
      }
    }
  }

  const renameChat = (id: string, newTitle: string) => {
    storage.renameConversation(id, newTitle)
    refreshConversations()
  }

  const togglePinChat = (id: string) => {
    storage.togglePin(id)
    refreshConversations()
  }

  const addMessage = (message: Message) => {
    if (!activeConversationId) {
      // Create new conversation if none exists
      const newConversation = storage.createConversation(message)
      setActiveConversationId(newConversation.id)
    } else {
      storage.addMessage(activeConversationId, message)
    }
    refreshConversations()
  }

  const setMode = (mode: string) => {
    setCurrentMode(mode)
  }

  const toggleConversationLanguage = async (): Promise<void> => {
    if (!activeConversationId) return
    
    try {
      const response = await fetch(`/api/conversation/${activeConversationId}/language/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (response.ok) {
        const result = await response.json()
        setConversationLanguageState(result.new_language)
      }
    } catch (error) {
      console.error('Failed to toggle conversation language:', error)
    }
  }

  const setConversationLanguage = async (lang: 'bn' | 'en'): Promise<void> => {
    if (!activeConversationId) return
    
    try {
      const response = await fetch(`/api/conversation/${activeConversationId}/language`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: lang })
      })
      
      if (response.ok) {
        setConversationLanguageState(lang)
      }
    } catch (error) {
      console.error('Failed to set conversation language:', error)
    }
  }

  const value: ChatContextType = {
    conversations,
    activeConversationId,
    activeConversation,
    currentMode,
    isLoading,
    conversationLanguage,
    createNewChat,
    switchToChat,
    deleteChat,
    renameChat,
    togglePinChat,
    addMessage,
    refreshConversations,
    setMode,
    toggleConversationLanguage,
    setConversationLanguage
  }

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  const context = useContext(ChatContext)
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}