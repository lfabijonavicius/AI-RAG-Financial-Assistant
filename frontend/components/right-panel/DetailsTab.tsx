"use client"

import type { ToolCall, PinnedTicker } from "@/lib/types"
import Sparkline from "@/components/right-panel/Sparkline"

interface Props {
  toolCalls: ToolCall[]
  pinnedTicker?: PinnedTicker | null
  pinnedLoading?: boolean
  onClearPinned?: () => void
}

function formatNum(v: unknown, prefix = ""): string {
  if (v === null || v === undefined) return "—"
  const n = Number(v)
  if (isNaN(n)) return String(v)
  if (n >= 1e12) return `${prefix}${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `${prefix}${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `${prefix}${(n / 1e6).toFixed(2)}M`
  return `${prefix}${n.toFixed(2)}`
}

interface StatCardProps {
  label: string
  value: string
  positive?: boolean | null
}

function StatCard({ label, value, positive }: StatCardProps) {
  const color = positive === null || positive === undefined
    ? "var(--text-primary)"
    : positive ? "#22c55e" : "#ef4444"

  return (
    <div className="rounded-xl p-3" style={{ backgroundColor: "var(--surface-2)" }}>
      <p className="text-xs mb-1" style={{ color: "var(--text-secondary)" }}>{label}</p>
      <p className="text-lg font-bold font-mono-numbers" style={{ color }}>{value}</p>
    </div>
  )
}

export default function DetailsTab({ toolCalls, pinnedTicker, pinnedLoading, onClearPinned }: Props) {
  // Loading state while fetching pinned ticker
  if (pinnedLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex gap-1">
          {[0, 1, 2].map(i => (
            <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce"
              style={{ backgroundColor: "var(--color-teal)", animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    )
  }

  // Pinned ticker view — shown when user clicks a ticker chip in a message
  if (pinnedTicker) {
    const pos = (pinnedTicker.total_return_pct ?? 0) >= 0
    const rows: [string, string, boolean?][] = [
      ["Price", pinnedTicker.price != null ? `$${Number(pinnedTicker.price).toFixed(2)}` : "—"],
      ["P/E", pinnedTicker.pe_ratio ? `${Number(pinnedTicker.pe_ratio).toFixed(1)}x` : "—"],
      ["Fwd P/E", pinnedTicker.forward_pe ? `${Number(pinnedTicker.forward_pe).toFixed(1)}x` : "—"],
      ["EPS", pinnedTicker.eps ? `$${Number(pinnedTicker.eps).toFixed(2)}` : "—"],
      ["Mkt Cap", formatNum(pinnedTicker.market_cap, "$")],
      ["Div Yield", pinnedTicker.dividend_yield ? `${(Number(pinnedTicker.dividend_yield) * 100).toFixed(2)}%` : "—"],
      ["52w High", formatNum(pinnedTicker["52w_high"], "$")],
      ["52w Low", formatNum(pinnedTicker["52w_low"], "$")],
    ]
    return (
      <div className="px-4 py-4 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold tracking-wider mb-0.5" style={{ color: "var(--color-teal)" }}>● PINNED</p>
            <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{pinnedTicker.ticker}</p>
            {pinnedTicker.name && (
              <p className="text-xs leading-tight mt-0.5" style={{ color: "var(--text-secondary)" }}>{pinnedTicker.name}</p>
            )}
          </div>
          {pinnedTicker.total_return_pct != null && (
            <span className="text-sm font-bold font-mono-numbers px-2 py-1 rounded-lg"
              style={{ color: pos ? "#22c55e" : "#ef4444", backgroundColor: pos ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)" }}>
              {pos ? "+" : ""}{pinnedTicker.total_return_pct.toFixed(2)}%
            </span>
          )}
        </div>

        {/* Sparkline */}
        {pinnedTicker.history.length > 1 && (
          <div className="rounded-xl p-3" style={{ backgroundColor: "var(--surface-2)" }}>
            <p className="text-xs mb-2" style={{ color: "var(--text-secondary)" }}>1-month price trend</p>
            <Sparkline data={pinnedTicker.history} width={220} height={50} />
          </div>
        )}

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-2">
          {rows.map(([label, value]) => (
            <StatCard key={label} label={label} value={value} />
          ))}
        </div>

        {/* Clear button */}
        <button onClick={onClearPinned}
          className="w-full text-xs py-1.5 rounded-lg transition-opacity hover:opacity-75"
          style={{ color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
          Clear
        </button>
      </div>
    )
  }

  if (!toolCalls.length) {
    return (
      <p className="text-xs px-4 py-6 text-center" style={{ color: "var(--text-secondary)" }}>
        No tool results yet. Ask about a stock to see details here.
      </p>
    )
  }

  // Find most relevant tool calls
  const fundamentals = toolCalls.findLast(tc => tc.tool === "get_fundamentals")?.args as Record<string, unknown> | undefined
  const price = toolCalls.findLast(tc => tc.tool === "get_stock_price")?.args as Record<string, unknown> | undefined
  const history = toolCalls.findLast(tc => tc.tool === "get_stock_history")?.args as Record<string, unknown> | undefined

  const data = fundamentals ?? price ?? (toolCalls[toolCalls.length - 1].args as Record<string, unknown>)
  const ticker = data.ticker as string | undefined
  const totalReturn = history?.total_return_pct as number | undefined

  // Build sparkline from history data
  const histData = history
    ? Object.values((history.data ?? {}) as Record<string, Record<string, number>>)
        .map(row => row.Close ?? row.close).filter(Boolean)
    : []

  const stats: { label: string; value: string; positive?: boolean | null }[] = []

  if (ticker) stats.push({ label: "Ticker", value: ticker })
  if (data.price) stats.push({ label: "Price", value: formatNum(data.price, "$") })
  if (data.pe_ratio) stats.push({ label: "P/E", value: `${Number(data.pe_ratio).toFixed(1)}x` })
  if (totalReturn !== undefined) stats.push({ label: "Return", value: `${totalReturn > 0 ? "+" : ""}${totalReturn?.toFixed(1)}%`, positive: totalReturn >= 0 })
  if (data.market_cap) stats.push({ label: "Market cap", value: formatNum(data.market_cap, "$") })
  if (data["52w_high"]) stats.push({ label: "52w high", value: formatNum(data["52w_high"], "$") })
  if (data["52w_low"]) stats.push({ label: "52w low", value: formatNum(data["52w_low"], "$") })
  if (data["50d_avg"]) stats.push({ label: "50d avg", value: formatNum(data["50d_avg"], "$") })

  return (
    <div className="px-4 py-4 space-y-4">
      {histData.length > 1 && (
        <div className="rounded-xl p-3" style={{ backgroundColor: "var(--surface-2)" }}>
          <p className="text-xs mb-2" style={{ color: "var(--text-secondary)" }}>{ticker} — Price trend</p>
          <Sparkline data={histData} width={220} height={50} />
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {stats.map(s => (
          <StatCard key={s.label} label={s.label} value={s.value} positive={s.positive} />
        ))}
      </div>
    </div>
  )
}
