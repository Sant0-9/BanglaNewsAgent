import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "../src/app/globals.css"
import { cn } from "@/lib/utils"
import { ThemeProvider } from "../components/providers"
import { SiteHeader } from "../components/site-header"
import { Toaster } from "@/components/ui/sonner"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono", 
  subsets: ["latin"],
})

export const viewport = "width=device-width, initial-scale=1";

export const themeColor = [
  { media: "(prefers-color-scheme: light)", color: "#ffffff" },
  { media: "(prefers-color-scheme: dark)", color: "#090826" }
];

export const metadata: Metadata = {
  title: "KhoborAgent - News Assistant",
  description: "Smart news aggregation and Q&A system supporting multiple languages and intents",
  keywords: ["news", "assistant", "Bangla", "multi-intent", "weather", "markets"],
  authors: [{ name: "KhoborAgent Team" }],
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-16x16.png", 
    apple: "/apple-touch-icon.png",
  },
}

interface RootLayoutProps {
  children: React.ReactNode
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          geistSans.variable,
          geistMono.variable
        )}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange
        >
          <div className="relative flex min-h-screen flex-col">
            <SiteHeader />
            <main className="flex-1">
              {children}
            </main>
          </div>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}