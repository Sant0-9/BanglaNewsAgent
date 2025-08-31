"use client"

import { createContext, useContext, useEffect, useState } from "react"

type Theme = "dark" | "light" | "system"

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: Theme
  storageKey?: string
  attribute?: string
  disableTransitionOnChange?: boolean
}

type ThemeProviderState = {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const initialState: ThemeProviderState = {
  theme: "dark", // Default to dark theme
  setTheme: () => null,
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)

export function ThemeProvider({
  children,
  defaultTheme = "dark", // Dark-first
  storageKey = "khobor-ui-theme",
  attribute = "class",
  disableTransitionOnChange = false,
  ...props
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(defaultTheme)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted) return

    const root = window.document.documentElement

    // Remove existing theme classes
    root.classList.remove("light", "dark")

    if (theme === "system") {
      const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"

      root.classList.add(systemTheme)
      return
    }

    root.classList.add(theme)
  }, [theme, mounted])

  const value = {
    theme,
    setTheme: (theme: Theme) => {
      // Store in localStorage
      try {
        localStorage.setItem(storageKey, theme)
      } catch (e) {
        // Silently fail if localStorage is not available
        console.warn("Failed to save theme to localStorage:", e)
      }
      
      setTheme(theme)
    },
  }

  // Load theme from localStorage on mount
  useEffect(() => {
    try {
      const storedTheme = localStorage.getItem(storageKey) as Theme
      if (storedTheme && ["dark", "light", "system"].includes(storedTheme)) {
        setTheme(storedTheme)
      } else {
        // Default to dark if no valid stored theme
        setTheme("dark")
      }
    } catch (e) {
      // If localStorage fails, use default dark theme
      console.warn("Failed to load theme from localStorage:", e)
      setTheme("dark")
    }
  }, [storageKey])

  // Handle system theme changes
  useEffect(() => {
    if (theme !== "system") return

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
    const handleChange = () => {
      const root = window.document.documentElement
      root.classList.remove("light", "dark")
      
      const systemTheme = mediaQuery.matches ? "dark" : "light"
      root.classList.add(systemTheme)
    }

    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [theme])

  // Prevent hydration mismatch by not rendering until mounted
  if (!mounted) {
    return (
      <div className="bg-bg-primary text-text-primary">
        {children}
      </div>
    )
  }

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext)

  if (context === undefined)
    throw new Error("useTheme must be used within a ThemeProvider")

  return context
}