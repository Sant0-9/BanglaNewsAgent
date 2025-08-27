import Image from "next/image"
import React from "react"
import type { Source } from "../lib/types"
import { cn } from "@/lib/utils"

function timeAgo(iso?: string | null): string {
  if (!iso) return ""
  const ts = Date.parse(iso)
  if (Number.isNaN(ts)) return ""
  const deltaSec = Math.max(1, Math.floor((Date.now() - ts) / 1000))
  const minutes = Math.floor(deltaSec / 60)
  const hours = Math.floor(deltaSec / 3600)
  const days = Math.floor(deltaSec / 86400)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

export function SourceList({ sources, className }: { sources: Source[]; className?: string }) {
  if (!sources || sources.length === 0) return null

  return (
    <div className={cn("grid gap-2", className)}>
      {sources.map((s, idx) => (
        <a
          key={`${s.url}-${idx}`}
          href={s.url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/90 shadow-sm transition hover:bg-white/10"
        >
          <div className="h-8 w-8 shrink-0 overflow-hidden rounded-lg bg-white/10 ring-1 ring-white/15">
            {s.logo ? (
              <Image src={s.logo} alt={s.name} width={32} height={32} className="h-8 w-8 object-cover" />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center text-xs text-white/70">{s.name?.[0] || ""}</div>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="truncate font-medium text-white">{s.name}</span>
              <span className="rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] text-yellow-300">[{idx + 1}]</span>
            </div>
            <div className="text-xs text-white/60">
              {timeAgo(s.published_at)}
            </div>
          </div>
        </a>
      ))}
    </div>
  )
}
