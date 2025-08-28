import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Toaster } from "@/components/ui/sonner"
import { ThemeProvider } from "@/components/providers/theme-provider"
import { cn } from "@/lib/utils"

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
})

export const metadata: Metadata = {
  title: "KhoborAgent - News Assistant",
  description: "Smart news aggregation and Q&A system supporting multiple languages and intents",
  keywords: ["news", "assistant", "Bangla", "multi-intent", "weather", "markets"],
  authors: [{ name: "KhoborAgent Team" }],
  viewport: "width=device-width, initial-scale=1",
  themeColor: "#090826",
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-16x16.png",
    apple: "/apple-touch-icon.png",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          inter.variable
        )}
      >
        <ThemeProvider
          defaultTheme="dark"
          storageKey="khobor-ui-theme"
          attribute="class"
          disableTransitionOnChange={false}
        >
          {children}
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}