"use client"

import { useEffect, useState } from "react"
import { Container } from "./container"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Toggle } from "@/components/ui/toggle"
import { Moon, Sun, Github, MessageCircle } from "lucide-react"
import { useTheme } from "next-themes"
import { cn } from "@/lib/utils"

const ROUTE_BADGES = [
  { label: "News", active: true },
  { label: "Weather", active: false },
  { label: "Markets", active: false },
  { label: "Sports", active: false },
  { label: "Lookup", active: false },
]

export function SiteHeader() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
      <Container>
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center space-x-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-white">
              <MessageCircle className="h-4 w-4" />
            </div>
            <span className="font-bold text-lg gradient-text">
              KhoborAgent
            </span>
          </div>

          {/* Center - Route Badges */}
          <div className="hidden sm:flex items-center space-x-2">
            {ROUTE_BADGES.map((route) => (
              <Badge
                key={route.label}
                variant={route.active ? "brand" : "outline"}
                className={cn(
                  "text-xs px-3 py-1 transition-colors cursor-pointer",
                  route.active 
                    ? "bg-brand-500/20 text-brand-400 border-brand-500/30" 
                    : "text-muted-foreground hover:text-foreground hover:border-foreground/20"
                )}
              >
                {route.label}
              </Badge>
            ))}
          </div>

          {/* Right - Theme Toggle + GitHub */}
          <div className="flex items-center space-x-2">
            <Toggle
              size="sm"
              pressed={mounted ? theme === "dark" : false}
              onPressedChange={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label="Toggle theme"
              className="h-9 w-9"
            >
              {!mounted ? (
                <Sun className="h-4 w-4" />
              ) : theme === "dark" ? (
                <Moon className="h-4 w-4" />
              ) : (
                <Sun className="h-4 w-4" />
              )}
            </Toggle>
            
            <Button
              variant="ghost"
              size="sm"
              className="h-9 w-9 p-0"
              asChild
            >
              <a
                href="#"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="GitHub repository"
              >
                <Github className="h-4 w-4" />
              </a>
            </Button>
          </div>
        </div>

        {/* Mobile Route Badges */}
        <div className="flex sm:hidden items-center space-x-2 pb-3 overflow-x-auto">
          {ROUTE_BADGES.map((route) => (
            <Badge
              key={route.label}
              variant={route.active ? "brand" : "outline"}
              className={cn(
                "text-xs px-3 py-1 transition-colors cursor-pointer whitespace-nowrap",
                route.active 
                  ? "bg-brand-500/20 text-brand-400 border-brand-500/30" 
                  : "text-muted-foreground hover:text-foreground hover:border-foreground/20"
              )}
            >
              {route.label}
            </Badge>
          ))}
        </div>
      </Container>
    </header>
  )
}