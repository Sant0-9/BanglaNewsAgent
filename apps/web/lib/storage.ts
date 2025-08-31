export interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  timestamp: Date
  intent?: string
  confidence?: number
  sources?: Array<{
    name: string
    url: string
  }>
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
  isPinned: boolean
}

class Storage {
  private readonly CONVERSATIONS_KEY = 'khobor-conversations'
  private readonly ACTIVE_CHAT_KEY = 'khobor-active-chat'

  // Get all conversations
  getConversations(): Conversation[] {
    try {
      const stored = localStorage.getItem(this.CONVERSATIONS_KEY)
      if (!stored) return []
      
      const conversations = JSON.parse(stored) as Conversation[]
      // Convert string dates back to Date objects
      return conversations.map(conv => ({
        ...conv,
        createdAt: new Date(conv.createdAt),
        updatedAt: new Date(conv.updatedAt),
        messages: conv.messages.map(msg => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }))
      }))
    } catch (error) {
      console.error('Failed to load conversations:', error)
      return []
    }
  }

  // Get a specific conversation by ID
  getConversation(id: string): Conversation | null {
    const conversations = this.getConversations()
    return conversations.find(conv => conv.id === id) || null
  }

  // Save all conversations
  private saveConversations(conversations: Conversation[]): void {
    try {
      localStorage.setItem(this.CONVERSATIONS_KEY, JSON.stringify(conversations))
    } catch (error) {
      console.error('Failed to save conversations:', error)
    }
  }

  // Create a new conversation
  createConversation(firstMessage?: Message): Conversation {
    const now = new Date()
    const conversation: Conversation = {
      id: `conv_${Date.now()}_${Math.random().toString(36).substring(7)}`,
      title: this.generateTitle(firstMessage?.content || 'New Chat'),
      messages: firstMessage ? [firstMessage] : [],
      createdAt: now,
      updatedAt: now,
      isPinned: false
    }

    const conversations = this.getConversations()
    conversations.unshift(conversation) // Add to beginning
    this.saveConversations(conversations)
    this.setActiveChat(conversation.id)
    
    return conversation
  }

  // Update an existing conversation
  updateConversation(id: string, updates: Partial<Conversation>): Conversation | null {
    const conversations = this.getConversations()
    const index = conversations.findIndex(conv => conv.id === id)
    
    if (index === -1) return null

    conversations[index] = {
      ...conversations[index],
      ...updates,
      updatedAt: new Date()
    }

    this.saveConversations(conversations)
    return conversations[index]
  }

  // Add a message to a conversation
  addMessage(conversationId: string, message: Message): Conversation | null {
    const conversations = this.getConversations()
    const conversation = conversations.find(conv => conv.id === conversationId)
    
    if (!conversation) return null

    conversation.messages.push(message)
    conversation.updatedAt = new Date()
    
    // Auto-update title based on first user message if still default
    if (conversation.title === 'New Chat' && message.role === 'user' && conversation.messages.length === 1) {
      conversation.title = this.generateTitle(message.content)
    }

    this.saveConversations(conversations)
    return conversation
  }

  // Delete a conversation
  deleteConversation(id: string): boolean {
    const conversations = this.getConversations()
    const filteredConversations = conversations.filter(conv => conv.id !== id)
    
    if (filteredConversations.length === conversations.length) {
      return false // Conversation not found
    }

    this.saveConversations(filteredConversations)
    
    // If this was the active chat, clear it
    if (this.getActiveChat() === id) {
      this.clearActiveChat()
    }
    
    return true
  }

  // Toggle pin status
  togglePin(id: string): boolean {
    const conversation = this.getConversation(id)
    if (!conversation) return false

    const updated = this.updateConversation(id, { isPinned: !conversation.isPinned })
    return updated !== null
  }

  // Rename conversation
  renameConversation(id: string, newTitle: string): boolean {
    const updated = this.updateConversation(id, { title: newTitle.trim() || 'Untitled Chat' })
    return updated !== null
  }

  // Active chat management
  getActiveChat(): string | null {
    try {
      return localStorage.getItem(this.ACTIVE_CHAT_KEY)
    } catch (error) {
      console.error('Failed to get active chat:', error)
      return null
    }
  }

  setActiveChat(id: string): void {
    try {
      localStorage.setItem(this.ACTIVE_CHAT_KEY, id)
    } catch (error) {
      console.error('Failed to set active chat:', error)
    }
  }

  clearActiveChat(): void {
    try {
      localStorage.removeItem(this.ACTIVE_CHAT_KEY)
    } catch (error) {
      console.error('Failed to clear active chat:', error)
    }
  }

  // Generate a title from message content (first 50 chars)
  private generateTitle(content: string): string {
    const cleaned = content.trim().replace(/\s+/g, ' ')
    if (cleaned.length <= 50) return cleaned
    return cleaned.substring(0, 47) + '...'
  }

  // Clear all data (for testing/reset)
  clearAll(): void {
    try {
      localStorage.removeItem(this.CONVERSATIONS_KEY)
      localStorage.removeItem(this.ACTIVE_CHAT_KEY)
    } catch (error) {
      console.error('Failed to clear storage:', error)
    }
  }

  // Get conversations sorted by pinned status and update time
  getConversationsSorted(): Conversation[] {
    const conversations = this.getConversations()
    return conversations.sort((a, b) => {
      // Pinned conversations first
      if (a.isPinned !== b.isPinned) {
        return a.isPinned ? -1 : 1
      }
      // Then by most recent update
      return b.updatedAt.getTime() - a.updatedAt.getTime()
    })
  }
}

// Export singleton instance
export const storage = new Storage()

// Export types for external use
export type { Conversation, Message }