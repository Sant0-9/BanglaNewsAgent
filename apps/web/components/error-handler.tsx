"use client"

import { toast } from "sonner"
import { useEffect } from "react"

interface ErrorHandlerProps {
  error?: Error | string | null
  context?: string
}

export function showErrorToast(error: Error | string, context?: string) {
  const message = error instanceof Error ? error.message : error
  
  toast.error(`${context ? `${context}: ` : ""}${message}`, {
    duration: 5000,
    closeButton: true,
    style: {
      background: 'rgba(239, 68, 68, 0.1)',
      border: '1px solid rgba(239, 68, 68, 0.3)',
      color: 'white',
    }
  })
}

export function showAbortToast() {
  toast.warning("Request was cancelled", {
    duration: 3000,
    closeButton: true,
    style: {
      background: 'rgba(245, 158, 11, 0.1)',
      border: '1px solid rgba(245, 158, 11, 0.3)',
      color: 'white',
    }
  })
}

export function showSuccessToast(message: string) {
  toast.success(message, {
    duration: 3000,
    style: {
      background: 'rgba(34, 197, 94, 0.1)',
      border: '1px solid rgba(34, 197, 94, 0.3)',
      color: 'white',
    }
  })
}

export function ErrorHandler({ error, context }: ErrorHandlerProps) {
  useEffect(() => {
    if (error) {
      showErrorToast(error, context)
    }
  }, [error, context])

  return null
}