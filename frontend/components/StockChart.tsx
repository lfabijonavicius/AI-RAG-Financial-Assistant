"use client"

import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, CartesianGrid,
} from "recharts"
import { useMemo } from "react"

interface DataPoint {
  date: string
  close: number
}

// For multi-ticker comparison: { date, AAPL: 100, MSFT: 97.3, ... }
interface MultiPoint {
  date: string
  [ticker: string]: string | number
}

interface SingleProps {
  ticker: string
  data: DataPoint[]
  returnPct?: number
}

interface MultiProps {
  tickers: string[]
  data: MultiPoint[]
  returns?: Record<string, number>
}

// Palette for multi-line chart
const COLORS = ["#1D9E75", "#8B5CF6", "#F59E0B", "#3B82F6", "#EC4899"]

function SingleTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const value: number = payload[0].value
  return (
    <div className="px-3 py-2 rounded-xl shadow-lg text-xs"
      style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)", minWidth: 120 }}>
      <p className="mb-1" style={{ color: "var(--text-secondary)" }}>{label}</p>
      <p className="text-sm font-bold font-mono-numbers" style={{ color: "var(--text-primary)" }}>
        ${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </p>
    </div>
  )
}

function MultiTooltip({ active, payload, label, tickers }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="px-3 py-2 rounded-xl shadow-lg text-xs"
      style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)", minWidth: 140 }}>
      <p className="mb-2 font-medium" style={{ color: "var(--text-secondary)" }}>{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center justify-between gap-4 mb-0.5">
          <span className="font-bold" style={{ color: entry.color }}>{entry.dataKey}</span>
          <span className="font-mono-numbers font-semibold" style={{ color: "var(--text-primary)" }}>
            {Number(entry.value).toFixed(1)}
          </span>
        </div>
      ))}
      <p className="mt-1.5 text-[10px]" style={{ color: "var(--text-secondary)" }}>normalised · 100 = start</p>
    </div>
  )
}

export function MultiStockChart({ tickers, data, returns }: MultiProps) {
  const tickInterval = Math.max(1, Math.floor(data.length / 6))

  return (
    <div style={{ width: "100%" }}>
      {/* Legend */}
      <div className="flex flex-wrap gap-3 mb-3">
        {tickers.map((t, i) => {
          const ret = returns?.[t]
          const pos = (ret ?? 0) >= 0
          return (
            <div key={t} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
              <span className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>{t}</span>
              {ret != null && (
                <span className="text-xs font-mono-numbers font-semibold" style={{ color: pos ? "#22c55e" : "#ef4444" }}>
                  {pos ? "+" : ""}{ret.toFixed(2)}%
                </span>
              )}
            </div>
          )
        })}
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.4} strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
            tickLine={false}
            axisLine={false}
            interval={tickInterval}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
            tickLine={false}
            axisLine={false}
            width={42}
            tickFormatter={(v) => `${Number(v).toFixed(0)}`}
          />
          <ReferenceLine y={100} stroke="var(--border)" strokeDasharray="4 3" />
          <Tooltip content={<MultiTooltip tickers={tickers} />} cursor={{ stroke: "var(--border)", strokeWidth: 1 }} />
          {tickers.map((t, i) => (
            <Line
              key={t}
              type="monotone"
              dataKey={t}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: "var(--surface-2)", strokeWidth: 2 }}
              isAnimationActive={true}
              animationDuration={700}
              animationEasing="ease-out"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function StockChart({ ticker, data, returnPct }: SingleProps) {
  const isPositive = (returnPct ?? 0) >= 0
  const color = isPositive ? "#1D9E75" : "#ef4444"
  const gradientId = `grad-${ticker}-${isPositive ? "pos" : "neg"}`

  const { minVal, maxVal, openPrice } = useMemo(() => {
    const prices = data.map(d => d.close)
    const minVal = Math.min(...prices)
    const maxVal = Math.max(...prices)
    const padding = (maxVal - minVal) * 0.12
    return { minVal: minVal - padding, maxVal: maxVal + padding, openPrice: prices[0] }
  }, [data])

  const tickInterval = Math.max(1, Math.floor(data.length / 6))

  return (
    <div style={{ width: "100%" }}>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.25} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="var(--border)" strokeOpacity={0.4} strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--text-secondary)" }} tickLine={false} axisLine={false} interval={tickInterval} />
          <YAxis
            domain={[minVal, maxVal]}
            tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
            tickLine={false}
            axisLine={false}
            width={58}
            tickFormatter={(v) => v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${Number(v).toFixed(0)}`}
          />
          <Tooltip content={<SingleTooltip />} cursor={{ stroke: color, strokeWidth: 1, strokeDasharray: "4 2" }} />
          <ReferenceLine y={openPrice} stroke={color} strokeOpacity={0.3} strokeDasharray="4 3" />
          <Area
            type="monotone" dataKey="close" stroke={color} strokeWidth={2}
            fill={`url(#${gradientId})`} dot={false}
            activeDot={{ r: 4, fill: color, stroke: "var(--surface-2)", strokeWidth: 2 }}
            isAnimationActive={true} animationDuration={700} animationEasing="ease-out"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
