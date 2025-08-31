"use client"

import { useState } from 'react'
import { AskRequest, AskResponse, ApiError } from '../types/api'

export function useApi() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ask = async (request: AskRequest): Promise<AskResponse | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        const errorData: ApiError = await response.json()
        throw new Error(errorData.error || `HTTP ${response.status}`)
      }

      const data: AskResponse = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('API Error:', err)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  return {
    ask,
    isLoading,
    error,
    clearError: () => setError(null),
  }
}