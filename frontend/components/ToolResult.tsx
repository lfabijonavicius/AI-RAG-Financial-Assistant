"use client"

import dynamic from "next/dynamic"
import { useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import type { ToolCall, RagProcess } from "@/lib/types"

const StockChart = dynamic(() => import("@/components/StockChart"), { ssr: false })
const MultiStockChart = dynamic(
  () => import("@/components/StockChart").then(m => ({ default: m.MultiStockChart })),
  { ssr: false }
)

interface Props {
  toolCalls: ToolCall[]
  onTickerClick?: (ticker: string) => void
}

function PriceCard({ ticker, price, change, onTickerClick }: { ticker: string; price?: number; change?: number; onTickerClick?: (t: string) => void }) {
  const pos = (change ?? 0) >= 0
  return (
    <div className="rounded-xl p-3" style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}>
      <button onClick={() => onTickerClick?.(ticker)} className="text-left hover:opacity-75 transition-opacity w-full">
        <p className="text-base font-bold font-mono-numbers" style={{ color: "var(--text-primary)" }}>
          {ticker}
        </p>
        {price != null && (
          <p className="text-xl font-bold font-mono-numbers" style={{ color: "var(--color-teal)" }}>
            ${Number(price).toFixed(2)}
          </p>
        )}
      </button>
      {change != null && (
        <span className="text-xs font-bold font-mono-numbers mt-1.5 inline-block px-2 py-0.5 rounded-full"
          style={{ color: pos ? "#22c55e" : "#ef4444", backgroundColor: pos ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)" }}>
          {pos ? "+" : ""}{Number(change).toFixed(1)}%
        </span>
      )}
    </div>
  )
}

function fmt(v: unknown, prefix = ""): string {
  if (v == null) return "—"
  const n = Number(v)
  if (isNaN(n)) return String(v)
  if (n >= 1e12) return `${prefix}${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `${prefix}${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `${prefix}${(n / 1e6).toFixed(2)}M`
  return `${prefix}${n.toFixed(2)}`
}

function RagProcessCard({ process }: { process: RagProcess }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-xl p-3 space-y-2" style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>● KNOWLEDGE BASE SEARCH</p>
        <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
          {process.chunks.length} chunks · {[...new Set(process.chunks.map(c => c.source))].length} source{[...new Set(process.chunks.map(c => c.source))].length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Generated queries */}
      <div className="space-y-1">
        <p className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Generated queries</p>
        {process.queries.map((q, i) => (
          <div key={i} className="flex gap-2 text-xs">
            <span className="shrink-0 font-mono-numbers" style={{ color: "var(--color-teal)" }}>{i + 1}.</span>
            <span style={{ color: "var(--text-primary)" }}>{q}</span>
          </div>
        ))}
      </div>

      {/* Collapsible chunks */}
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1 text-xs transition-opacity hover:opacity-75"
        style={{ color: "var(--text-secondary)" }}
      >
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        {open ? "Hide" : "Show"} retrieved chunks
      </button>

      {open && (
        <div className="space-y-1.5 pt-1">
          {process.chunks.map((chunk, i) => (
            <div key={i} className="rounded-lg p-2.5" style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium truncate" style={{ color: "var(--color-teal)" }}>
                  📄 {chunk.source}
                </span>
                {chunk.similarity != null && (
                  <span className="text-xs font-mono-numbers shrink-0 ml-2"
                    style={{ color: chunk.similarity > 0.85 ? "#22c55e" : "var(--text-secondary)" }}>
                    {chunk.similarity.toFixed(2)}
                  </span>
                )}
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {chunk.content}…
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ToolResult({ toolCalls, onTickerClick }: Props) {
  if (!toolCalls.length) return null

  return (
    <div className="space-y-2">
      {toolCalls.map((tc, i) => {
        const data = (tc.result ?? {}) as Record<string, unknown>

        /* ── Compare stocks ── */
        if (tc.tool === "compare_stocks") {
          const comparison = (data.comparison ?? {}) as Record<string, Record<string, unknown>>
          const period = (data.period ?? tc.args.period ?? "1mo") as string
          const history = (data.history ?? {}) as Record<string, Record<string, number>>
          const tickers = Object.keys(comparison)
          if (data.error || !tickers.length) return null

          // Build merged chart data: [{ date, AAPL: 100, MSFT: 97.3 }, ...]
          const allDates = [...new Set(
            tickers.flatMap(t => Object.keys(history[t] ?? {}))
          )].sort()
          const chartData = allDates.map(date => {
            const point: { date: string } & Record<string, string | number> = { date }
            tickers.forEach(t => { if (history[t]?.[date] != null) point[t] = history[t][date] })
            return point
          })

          const returns: Record<string, number> = {}
          tickers.forEach(t => { returns[t] = comparison[t][`return_${period}_pct`] as number })

          return (
            <div key={i} className="rounded-xl p-4" style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}>
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>
                  ● STOCK COMPARISON
                </p>
                <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{period}</span>
              </div>
              {/* Price pills */}
              <div className="grid gap-2 mb-4" style={{ gridTemplateColumns: `repeat(${tickers.length}, 1fr)` }}>
                {tickers.map(t => (
                  <PriceCard key={t} ticker={t}
                    price={comparison[t].price as number}
                    change={returns[t]}
                    onTickerClick={onTickerClick} />
                ))}
              </div>
              {/* Multi-line chart */}
              {chartData.length > 1 && (
                <MultiStockChart tickers={tickers} data={chartData} returns={returns} />
              )}
            </div>
          )
        }

        /* ── Stock history (shows full chart) ── */
        if (tc.tool === "get_stock_history") {
          if (data.error) return null
          const rawData = (data.data ?? {}) as Record<string, Record<string, number>>
          const chartData = Object.entries(rawData).map(([date, row]) => ({
            date: date.slice(5),   // MM-DD
            close: row.Close ?? row.close,
          }))
          const ticker = (data.ticker ?? tc.args.ticker) as string
          const name = (data.name ?? ticker) as string
          const ret = data.total_return_pct as number | undefined
          const pos = (ret ?? 0) >= 0
          const periodLabel = (data.period ?? tc.args.period ?? "") as string
          if (chartData.length < 2) return null
          return (
            <div key={i} className="rounded-xl p-4" style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}>
              {/* Card header */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-xs font-semibold tracking-wider mb-0.5" style={{ color: "var(--color-teal)" }}>
                    ● PRICE HISTORY
                  </p>
                  <button onClick={() => onTickerClick?.(ticker)} className="text-base font-bold hover:opacity-75 transition-opacity" style={{ color: "var(--text-primary)" }}>{name}</button>
                </div>
                <div className="text-right">
                  {ret != null && (
                    <p className="text-lg font-bold font-mono-numbers" style={{ color: pos ? "#22c55e" : "#ef4444" }}>
                      {pos ? "+" : ""}{ret.toFixed(2)}%
                    </p>
                  )}
                  {periodLabel && (
                    <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{periodLabel}</p>
                  )}
                </div>
              </div>
              <StockChart ticker={ticker} data={chartData} returnPct={ret} />
            </div>
          )
        }

        /* ── Live price ── */
        if (tc.tool === "get_stock_price") {
          const price = data.price
          if (data.error || price == null || isNaN(Number(price))) return null
          const spTicker = (data.ticker ?? tc.args.ticker) as string
          return (
            <div key={i} className="rounded-xl p-3" style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}>
              <p className="text-xl font-bold font-mono-numbers" style={{ color: "var(--text-primary)" }}>
                <button onClick={() => onTickerClick?.(spTicker)} className="hover:opacity-75 transition-opacity text-left">
                  {(data.name ?? spTicker) as string}
                </button>
                <span className="ml-2" style={{ color: "var(--color-teal)" }}>${Number(price).toFixed(2)}</span>
              </p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-secondary)" }}>{data.market_state as string}</p>
            </div>
          )
        }

        /* ── Fundamentals ── */
        if (tc.tool === "get_fundamentals") {
          const fTicker = (data.ticker ?? tc.args.ticker) as string
          const rows: [string, string][] = [
            ["Ticker", fTicker ?? "—"],
            ["P/E", data.pe_ratio ? `${Number(data.pe_ratio).toFixed(1)}x` : "—"],
            ["Fwd P/E", data.forward_pe ? `${Number(data.forward_pe).toFixed(1)}x` : "—"],
            ["EPS", data.eps ? `$${data.eps}` : "—"],
            ["Mkt Cap", fmt(data.market_cap, "$")],
            ["Div Yield", data.dividend_yield ? `${(Number(data.dividend_yield)*100).toFixed(2)}%` : "—"],
            ["52w High", fmt(data["52w_high"], "$")],
            ["52w Low", fmt(data["52w_low"], "$")],
          ]
          return (
            <div key={i} className="rounded-xl p-3" style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}>
              {fTicker && (
                <button onClick={() => onTickerClick?.(fTicker)} className="text-xs font-semibold mb-2 tracking-wider hover:opacity-75 transition-opacity block" style={{ color: "var(--color-teal)" }}>
                  ● {fTicker} FUNDAMENTALS
                </button>
              )}
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                {rows.map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span style={{ color: "var(--text-secondary)" }}>{k}</span>
                    <span className="font-mono-numbers font-semibold" style={{ color: "var(--text-primary)" }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )
        }

        /* ── News (company or market) ── */
        if (tc.tool === "get_company_news" || tc.tool === "get_market_news") {
          const articles = Array.isArray(tc.result) ? tc.result as Record<string, string>[] : []
          if (!articles.length) return null
          const label = tc.tool === "get_market_news"
            ? `MARKET NEWS · ${(tc.args.topic as string ?? "").toUpperCase()}`
            : `NEWS · ${(tc.args.ticker as string ?? "").toUpperCase()}`
          return (
            <div key={i} className="rounded-xl p-3 space-y-2" style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}>
              <p className="text-xs font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>● {label}</p>
              <div className="space-y-1.5">
                {articles.map((a, j) => (
                  <a
                    key={j}
                    href={a.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block rounded-lg p-2.5 transition-opacity hover:opacity-75"
                    style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}
                  >
                    <p className="text-xs font-medium leading-snug" style={{ color: "var(--text-primary)" }}>{a.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs" style={{ color: "var(--color-teal)" }}>{a.source}</span>
                      {a.sentiment && (
                        <span className="text-xs px-1.5 py-0.5 rounded-full font-medium"
                          style={{
                            color: a.sentiment === "Bullish" || a.sentiment === "Somewhat-Bullish" ? "#22c55e"
                              : a.sentiment === "Bearish" || a.sentiment === "Somewhat-Bearish" ? "#ef4444"
                              : "var(--text-secondary)",
                            backgroundColor: a.sentiment === "Bullish" || a.sentiment === "Somewhat-Bullish" ? "rgba(34,197,94,0.1)"
                              : a.sentiment === "Bearish" || a.sentiment === "Somewhat-Bearish" ? "rgba(239,68,68,0.1)"
                              : "var(--surface)",
                          }}>
                          {a.sentiment}
                        </span>
                      )}
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )
        }

        /* ── RAG knowledge base search ── */
        if (tc.tool === "search_knowledge_base") {
          if (!tc.rag_process?.queries?.length || !tc.rag_process?.chunks) return null
          return <RagProcessCard key={i} process={tc.rag_process} />
        }

        /* ── Generic fallback — skip if error result or no useful args ── */
        if (data.error) return null
        const argStr = Object.entries(tc.args).slice(0, 3).map(([k, v]) => `${k}: ${v}`).join(", ")
        if (!argStr) return null
        return (
          <div key={i} className="rounded-xl px-3 py-2 text-xs"
            style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
            <span className="font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>
              ● {tc.tool.toUpperCase().replace(/_/g, " ")}
            </span>
            {" — "}
            {argStr}
          </div>
        )
      })}
    </div>
  )
}
