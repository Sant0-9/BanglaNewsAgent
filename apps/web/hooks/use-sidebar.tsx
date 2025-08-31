"use client"

import { useState, useEffect } from "react"

const SIDEBAR_STORAGE_KEY = "khobor-sidebar-collapsed"
const SIDEBAR_WIDTH_STORAGE_KEY = "khobor-sidebar-width"

export function useSidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(25) // Percentage
  const [isLoaded, setIsLoaded] = useState(false)

  // Load state from localStorage on mount
  useEffect(() => {
    try {
      const savedState = localStorage.getItem(SIDEBAR_STORAGE_KEY)
      if (savedState !== null) {
        setIsCollapsed(JSON.parse(savedState))
      }
      
      const savedWidth = localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY)
      if (savedWidth !== null) {
        setSidebarWidth(JSON.parse(savedWidth))
      }
    } catch (error) {
      console.warn("Failed to load sidebar state:", error)
    } finally {
      setIsLoaded(true)
    }
  }, [])

  // Save state to localStorage whenever it changes
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, JSON.stringify(isCollapsed))
      } catch (error) {
        console.warn("Failed to save sidebar state:", error)
      }
    }
  }, [isCollapsed, isLoaded])

  // Save width to localStorage whenever it changes
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, JSON.stringify(sidebarWidth))
      } catch (error) {
        console.warn("Failed to save sidebar width:", error)
      }
    }
  }, [sidebarWidth, isLoaded])

  const toggleSidebar = () => {
    setIsCollapsed(prev => !prev)
  }

  const handleSidebarResize = (newWidth: number) => {
    setSidebarWidth(newWidth)
  }

  return {
    isCollapsed,
    sidebarWidth,
    toggleSidebar,
    handleSidebarResize,
    isLoaded
  }
}