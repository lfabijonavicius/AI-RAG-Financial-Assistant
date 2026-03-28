"use client"

import { useEffect, useState, useRef } from "react"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

interface MarketItem {
  symbol: string
  name: string
  price: number
  change_pct: number
}

function TickerCard({ item }: { item: MarketItem }) {
  const pos = item.change_pct >= 0
  return (
    <div
      className="flex items-center gap-3 px-4 py-2 rounded-xl shrink-0"
      style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <span className="text-xs font-semibold" style={{ color: "var(--text-secondary)" }}>{item.name}</span>
      <span className="text-xs font-bold font-mono-numbers" style={{ color: "var(--text-primary)" }}>
        {item.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
      </span>
      <span
        className="text-xs font-bold font-mono-numbers px-1.5 py-0.5 rounded-full"
        style={{
          color: pos ? "#22c55e" : "#ef4444",
          backgroundColor: pos ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
        }}
      >
        {pos ? "▲" : "▼"} {Math.abs(item.change_pct).toFixed(2)}%
      </span>
    </div>
  )
}

export default function MarketTicker() {
  const [markets, setMarkets] = useState<MarketItem[]>([])
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function load() {
    try {
      const res = await fetch(`${BASE}/markets`)
      if (!res.ok) return
      const data = await res.json()
      setMarkets(data.markets ?? [])
    } catch { /* silently skip if backend unreachable */ }
  }

  useEffect(() => {
    load()
    intervalRef.current = setInterval(load, 60_000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [])

  if (!markets.length) return null

  // Duplicate items so the marquee loops seamlessly
  const items = [...markets, ...markets]

  return (
    <div className="w-full overflow-hidden" style={{ maskImage: "linear-gradient(to right, transparent, black 10%, black 90%, transparent)" }}>
      <div className="flex gap-3 animate-ticker w-max">
        {items.map((item, i) => (
          <TickerCard key={`${item.symbol}-${i}`} item={item} />
        ))}
      </div>
    </div>
  )
}
