"use client"

import { useState, useEffect, useCallback } from "react"
import { Plus, Trash2, RefreshCw, Pencil, Check, X } from "lucide-react"

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

function FieldInput({ placeholder, value, onChange }: { placeholder: string; value: string; onChange: (v: string) => void }) {
  return (
    <input
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-lg px-3 py-2 text-xs outline-none"
      style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
    />
  )
}

export default function PortfolioTab({ userId }: Props) {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingTicker, setEditingTicker] = useState<string | null>(null)

  // Add form state
  const [newTicker, setNewTicker] = useState("")
  const [newShares, setNewShares] = useState("")
  const [newPrice, setNewPrice] = useState("")
  const [addError, setAddError] = useState("")
  const [adding, setAdding] = useState(false)

  // Edit form state (per position)
  const [editShares, setEditShares] = useState("")
  const [editPrice, setEditPrice] = useState("")
  const [editError, setEditError] = useState("")
  const [saving, setSaving] = useState(false)

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

  async function upsertPosition(ticker: string, shares: number, avg_buy_price: number): Promise<boolean> {
    const res = await fetch(`${API}/portfolio`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, ticker, shares, avg_buy_price }),
    })
    return res.ok
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    setAddError("")
    const t = newTicker.trim().toUpperCase()
    const s = parseFloat(newShares)
    const p = parseFloat(newPrice)
    if (!t || isNaN(s) || s <= 0 || isNaN(p) || p <= 0) {
      setAddError("Enter a valid ticker, shares, and buy price.")
      return
    }
    setAdding(true)
    const ok = await upsertPosition(t, s, p)
    setAdding(false)
    if (ok) {
      setNewTicker(""); setNewShares(""); setNewPrice(""); setShowAddForm(false)
      load(true)
    }
  }

  function startEdit(pos: Position) {
    setEditingTicker(pos.ticker)
    setEditShares(pos.shares.toString())
    setEditPrice(pos.avg_buy_price.toString())
    setEditError("")
  }

  function cancelEdit() {
    setEditingTicker(null)
    setEditError("")
  }

  async function handleSaveEdit(ticker: string) {
    setEditError("")
    const s = parseFloat(editShares)
    const p = parseFloat(editPrice)
    if (isNaN(s) || s <= 0 || isNaN(p) || p <= 0) {
      setEditError("Enter valid shares and price.")
      return
    }
    setSaving(true)
    const ok = await upsertPosition(ticker, s, p)
    setSaving(false)
    if (ok) {
      setEditingTicker(null)
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

  const totalUp = portfolio && portfolio.total_pl >= 0

  return (
    <div className="px-4 py-4 space-y-3">
      {/* Summary */}
      {portfolio && portfolio.positions.length > 0 && (
        <div className="rounded-xl p-3" style={{ backgroundColor: "var(--surface-2)" }}>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>● PORTFOLIO</p>
            <button onClick={() => load(true)} disabled={refreshing} className="opacity-50 hover:opacity-100 transition-opacity">
              <RefreshCw size={12} style={{ color: "var(--text-secondary)" }} className={refreshing ? "animate-spin" : ""} />
            </button>
          </div>
          <p className="text-xl font-bold font-mono-numbers" style={{ color: "var(--text-primary)" }}>
            ${portfolio.total_value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs font-mono-numbers font-semibold" style={{ color: totalUp ? "#22c55e" : "#ef4444" }}>
              {totalUp ? "+" : ""}${Math.abs(portfolio.total_pl).toFixed(2)}
            </span>
            <span className="text-xs font-mono-numbers px-1.5 py-0.5 rounded-full"
              style={{ color: totalUp ? "#22c55e" : "#ef4444", backgroundColor: totalUp ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)" }}>
              {totalUp ? "+" : ""}{portfolio.total_pl_pct.toFixed(2)}%
            </span>
          </div>
        </div>
      )}

      {/* Positions */}
      {portfolio?.positions.map(p => {
        const up = p.pl >= 0
        const isEditing = editingTicker === p.ticker
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
              <div className="flex items-center gap-2 ml-2 shrink-0">
                {isEditing ? (
                  <>
                    <button onClick={() => handleSaveEdit(p.ticker)} disabled={saving}
                      className="opacity-60 hover:opacity-100 transition-opacity">
                      <Check size={13} style={{ color: "var(--color-teal)" }} />
                    </button>
                    <button onClick={cancelEdit} className="opacity-60 hover:opacity-100 transition-opacity">
                      <X size={13} style={{ color: "var(--text-secondary)" }} />
                    </button>
                  </>
                ) : (
                  <>
                    <button onClick={() => startEdit(p)} className="opacity-30 hover:opacity-80 transition-opacity">
                      <Pencil size={12} style={{ color: "var(--text-secondary)" }} />
                    </button>
                    <button onClick={() => handleRemove(p.ticker)} className="opacity-30 hover:opacity-80 transition-opacity">
                      <Trash2 size={13} style={{ color: "var(--text-secondary)" }} />
                    </button>
                  </>
                )}
              </div>
            </div>

            {isEditing ? (
              <div className="mt-2 space-y-1.5">
                {editError && <p className="text-xs" style={{ color: "#ef4444" }}>{editError}</p>}
                <FieldInput placeholder="Shares" value={editShares} onChange={setEditShares} />
                <FieldInput placeholder="Avg buy price" value={editPrice} onChange={setEditPrice} />
              </div>
            ) : (
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
            )}
          </div>
        )
      })}

      {/* Empty state */}
      {portfolio?.positions.length === 0 && !showAddForm && (
        <p className="text-xs text-center py-4" style={{ color: "var(--text-secondary)" }}>
          No positions yet. Add your first stock below.
        </p>
      )}

      {/* Add form */}
      {showAddForm ? (
        <form onSubmit={handleAdd} className="rounded-xl p-3 space-y-2"
          style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}>
          <p className="text-xs font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>ADD POSITION</p>
          {addError && <p className="text-xs" style={{ color: "#ef4444" }}>{addError}</p>}
          <FieldInput placeholder="Ticker (e.g. AAPL)" value={newTicker} onChange={setNewTicker} />
          <FieldInput placeholder="Shares (e.g. 10)" value={newShares} onChange={setNewShares} />
          <FieldInput placeholder="Avg buy price (e.g. 180.00)" value={newPrice} onChange={setNewPrice} />
          <div className="flex gap-2 pt-1">
            <button type="submit" disabled={adding}
              className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-opacity disabled:opacity-50"
              style={{ backgroundColor: "var(--color-teal)", color: "white" }}>
              {adding ? "Adding…" : "Add"}
            </button>
            <button type="button" onClick={() => { setShowAddForm(false); setAddError("") }}
              className="flex-1 py-1.5 rounded-lg text-xs font-semibold"
              style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button onClick={() => setShowAddForm(true)}
          className="w-full flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold transition-opacity hover:opacity-75"
          style={{ border: "1px dashed var(--border)", color: "var(--color-teal)" }}>
          <Plus size={13} /> Add position
        </button>
      )}
    </div>
  )
}
