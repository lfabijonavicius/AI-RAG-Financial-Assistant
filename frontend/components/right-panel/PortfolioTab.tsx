"use client"

import { useState, useEffect, useCallback } from "react"
import { Plus, Trash2, RefreshCw } from "lucide-react"

interface Position {
  id: string
  ticker: string
  name: string
  shares: number
  avg_buy_price: number
  current_price: number
  current_value: number
  cost_basis: number
  pl: number
  pl_pct: number
}

interface PortfolioSummary {
  positions: Position[]
  total_value: number
  total_cost: number
  total_pl: number
  total_pl_pct: number
}

interface Props {
  userId: string
}

const API = process.env.NEXT_PUBLIC_API_URL

function fmt(n: number, prefix = "") {
  if (n >= 1e6) return `${prefix}${(n / 1e6).toFixed(2)}M`
  if (n >= 1e3) return `${prefix}${(n / 1e3).toFixed(1)}k`
  return `${prefix}${n.toFixed(2)}`
}

export default function PortfolioTab({ userId }: Props) {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [ticker, setTicker] = useState("")
  const [shares, setShares] = useState("")
  const [buyPrice, setBuyPrice] = useState("")
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState("")

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    try {
      const res = await fetch(`${API}/portfolio/${userId}`)
      if (res.ok) setPortfolio(await res.json())
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [userId])

  useEffect(() => { load() }, [load])

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    const t = ticker.trim().toUpperCase()
    const s = parseFloat(shares)
    const p = parseFloat(buyPrice)
    if (!t || isNaN(s) || s <= 0 || isNaN(p) || p <= 0) {
      setError("Enter a valid ticker, shares, and buy price.")
      return
    }
    setAdding(true)
    const res = await fetch(`${API}/portfolio`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, ticker: t, shares: s, avg_buy_price: p }),
    })
    setAdding(false)
    if (res.ok) {
      setTicker(""); setShares(""); setBuyPrice(""); setShowForm(false)
      load(true)
    }
  }

  async function handleRemove(t: string) {
    await fetch(`${API}/portfolio/${userId}/${t}`, { method: "DELETE" })
    load(true)
  }

  if (loading) {
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

  const pos = portfolio && (portfolio.total_pl >= 0)

  return (
    <div className="px-4 py-4 space-y-3">
      {/* Summary header */}
      {portfolio && portfolio.positions.length > 0 && (
        <div className="rounded-xl p-3" style={{ backgroundColor: "var(--surface-2)" }}>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>● PORTFOLIO</p>
            <button onClick={() => load(true)} disabled={refreshing}
              className="opacity-50 hover:opacity-100 transition-opacity">
              <RefreshCw size={12} style={{ color: "var(--text-secondary)" }}
                className={refreshing ? "animate-spin" : ""} />
            </button>
          </div>
          <p className="text-xl font-bold font-mono-numbers" style={{ color: "var(--text-primary)" }}>
            ${portfolio.total_value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs font-mono-numbers font-semibold"
              style={{ color: pos ? "#22c55e" : "#ef4444" }}>
              {pos ? "+" : ""}${Math.abs(portfolio.total_pl).toFixed(2)}
            </span>
            <span className="text-xs font-mono-numbers px-1.5 py-0.5 rounded-full"
              style={{ color: pos ? "#22c55e" : "#ef4444", backgroundColor: pos ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)" }}>
              {pos ? "+" : ""}{portfolio.total_pl_pct.toFixed(2)}%
            </span>
          </div>
        </div>
      )}

      {/* Position list */}
      {portfolio?.positions.map(p => {
        const up = p.pl >= 0
        return (
          <div key={p.ticker} className="rounded-xl p-3" style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}>
            <div className="flex items-start justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{p.ticker}</span>
                  <span className="text-xs font-mono-numbers font-semibold px-1.5 py-0.5 rounded-full"
                    style={{ color: up ? "#22c55e" : "#ef4444", backgroundColor: up ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)" }}>
                    {up ? "+" : ""}{p.pl_pct.toFixed(2)}%
                  </span>
                </div>
                <p className="text-xs truncate mt-0.5" style={{ color: "var(--text-secondary)" }}>{p.name}</p>
              </div>
              <button onClick={() => handleRemove(p.ticker)}
                className="opacity-30 hover:opacity-80 transition-opacity ml-2 shrink-0">
                <Trash2 size={13} style={{ color: "var(--text-secondary)" }} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-2">
              {[
                ["Shares", p.shares.toString()],
                ["Price", `$${p.current_price.toFixed(2)}`],
                ["Value", fmt(p.current_value, "$")],
                ["Cost", fmt(p.cost_basis, "$")],
                ["P/L", `${up ? "+" : ""}$${Math.abs(p.pl).toFixed(2)}`],
                ["Avg Buy", `$${p.avg_buy_price.toFixed(2)}`],
              ].map(([label, val]) => (
                <div key={label} className="flex justify-between text-xs">
                  <span style={{ color: "var(--text-secondary)" }}>{label}</span>
                  <span className="font-mono-numbers font-semibold"
                    style={{ color: label === "P/L" ? (up ? "#22c55e" : "#ef4444") : "var(--text-primary)" }}>
                    {val}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )
      })}

      {/* Empty state */}
      {portfolio?.positions.length === 0 && !showForm && (
        <p className="text-xs text-center py-4" style={{ color: "var(--text-secondary)" }}>
          No positions yet. Add your first stock below.
        </p>
      )}

      {/* Add form */}
      {showForm ? (
        <form onSubmit={handleAdd} className="rounded-xl p-3 space-y-2"
          style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}>
          <p className="text-xs font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>ADD POSITION</p>
          {error && <p className="text-xs" style={{ color: "#ef4444" }}>{error}</p>}
          {[
            { placeholder: "Ticker (e.g. AAPL)", value: ticker, onChange: setTicker },
            { placeholder: "Shares (e.g. 10)", value: shares, onChange: setShares },
            { placeholder: "Avg buy price (e.g. 180.00)", value: buyPrice, onChange: setBuyPrice },
          ].map((field, i) => (
            <input key={i}
              value={field.value}
              onChange={e => field.onChange(e.target.value)}
              placeholder={field.placeholder}
              className="w-full rounded-lg px-3 py-2 text-xs outline-none"
              style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
            />
          ))}
          <div className="flex gap-2 pt-1">
            <button type="submit" disabled={adding}
              className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-opacity disabled:opacity-50"
              style={{ backgroundColor: "var(--color-teal)", color: "white" }}>
              {adding ? "Adding…" : "Add"}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setError("") }}
              className="flex-1 py-1.5 rounded-lg text-xs font-semibold"
              style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button onClick={() => setShowForm(true)}
          className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold transition-opacity hover:opacity-75"
          style={{ border: "1px dashed var(--border)", color: "var(--color-teal)" }}>
          <Plus size={13} /> Add position
        </button>
      )}
    </div>
  )
}
