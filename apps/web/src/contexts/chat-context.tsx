"use client"

import { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { storage, Conversation, Message } from "@/lib/storage"

interface ChatContextType {
  conversations: Conversation[]
  activeConversationId: string | null
  activeConversation: Conversation | null
  isLoading: boolean
  
  // Actions
  createNewChat: () => string
  switchToChat: (id: string) => void
  deleteChat: (id: string) => void
  renameChat: (id: string, newTitle: string) => void
  togglePinChat: (id: string) => void
  addMessage: (message: Message) => void
  refreshConversations: () => void
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export function ChatProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Get active conversation
  const activeConversation = conversations.find(conv => conv.id === activeConversationId) || null

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

  const value: ChatContextType = {
    conversations,
    activeConversationId,
    activeConversation,
    isLoading,
    createNewChat,
    switchToChat,
    deleteChat,
    renameChat,
    togglePinChat,
    addMessage,
    refreshConversations
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