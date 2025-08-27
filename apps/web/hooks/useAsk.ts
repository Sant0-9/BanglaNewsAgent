"use client"

import { useCallback, useMemo, useRef, useState } from 'react'
import type { AskResponse } from '../lib/types'
import { postAsk, type PostAskBody, type ApiError as ApiErrorClass, TimeoutError, AbortError } from '../lib/api'

export type UseAskOptions = {
  onChunk?: (delta: string) => void
  timeoutMs?: number
}

export function useAsk(options: UseAskOptions = {}) {
  const { onChunk, timeoutMs } = options

  const [response, setResponse] = useState<AskResponse | null>(null)
  const [pending, setPending] = useState(false)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)

  const clear = useCallback(() => {
    setResponse(null)
    setError(null)
  }, [])

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setPending(false)
    setPendingId(null)
  }, [])

  const ask = useCallback(async (query: string, lang: 'bn' | 'en', extra?: { mode?: 'brief' | 'deep'; window_hours?: number }) => {
    // Prevent parallel requests
    if (pendingId) {
      throw new Error('Another request is already in progress')
    }

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    const controller = new AbortController()
    abortControllerRef.current = controller

    const requestId = crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
    setPendingId(requestId)
    setPending(true)
    setError(null)

    const body: PostAskBody = { query, lang, ...extra }

    try {
      const data = await postAsk(body, {
        onDelta: onChunk, // Use onDelta for cleaner interface
        signal: controller.signal,
        config: timeoutMs ? { timeout: timeoutMs } : undefined,
      })

      setResponse(data)
      return data
    } catch (err) {
      let message = 'Something went wrong. Please try again.'

      if (err instanceof AbortError) {
        message = 'Request cancelled.'
      } else if (err instanceof TimeoutError) {
        message = 'Request timed out. Please try again.'
      } else if (err instanceof Error) {
        message = err.message
      }

      setError(message)
      throw err
    } finally {
      setPending(false)
      setPendingId(null)
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null
      }
    }
  }, [onChunk, timeoutMs, pendingId])

  return useMemo(() => ({
    response,
    pending,
    pendingId,
    error,
    ask,
    abort,
    clear,
  }), [response, pending, pendingId, error, ask, abort, clear])
}
