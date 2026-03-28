"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { Message } from "@/lib/types"
import ToolResult from "@/components/ToolResult"

// Common uppercase words that are NOT stock tickers
const SKIP_WORDS = new Set([
  "AN","AS","AT","BE","BY","DO","GO","HE","IF","IN","IS","IT","ME","MY",
  "NO","OF","ON","OR","SO","TO","UP","US","WE","OK","AI",
  "AND","ARE","BUT","CAN","FOR","HAS","HAD","HER","HIM","HIS","HOW","NOT",
  "NOW","OUR","OUT","OWN","SAY","SHE","THE","TOO","TWO","USE","WAS","WAY",
  "WHO","WHY","YOU","ITS","YES","NEW","OLD","BIG","KEY","TOP","TAX","NET",
  "LOW","MAX","MIN","AVG","PCT","PER","YOY","QOQ","MOM",
  "ALSO","BEEN","FROM","HAVE","HERE","INTO","MANY","MORE","MOST","MUCH",
  "NEXT","ONLY","OVER","SAME","SOME","SUCH","THAN","THAT","THEN","THEM",
  "THEY","THIS","VERY","WELL","WERE","WHAT","WITH","YOUR","WILL","JUST",
  "EVEN","BOTH","EACH","LESS","LIKE","LONG","ONCE","OPEN","PLAN","SHOW",
  "STILL","THUS","WHEN","HIGH","DOWN","RISK","YEAR","FUND","MADE","MAKE",
  "NEED","TAKE","RATE","BASE","CORE","REAL","COST","DATA","EARN","FALL",
  "FLOW","GAIN","GREW","GROW","HOLD","JOIN","KEEP","LEAD","LOSS","MOVE",
  "NEAR","NOTE","PAST","RISE","ROSE","SELL","SETS","SIDE","SIZE","SOLD",
  "TERM","TURN","TYPE","UNIT","USED","VIEW","WIDE","WORK","RISE","NEAR",
  "ETF","CEO","CFO","COO","CTO","EPS","GDP","USA","USD","EUR","GBP","WEF",
  "ESG","IPO","PDF","API","LLM","RAG","IRS","SEC","NAV","AUM","YTD","TTM",
  "CAGR","WACC","EBIT","FCF","ROE","ROI","DCF","VIX","EBITDA","PE","PEG",
  "INC","CORP","LTD","LLC","PLC","GROUP","FORM","ENDED","YEAR","FISCAL",
  "ANNUAL","REPORT","TESLA","APPLE","MICROSOFT","ALPHABET","AMAZON","NVIDIA",
  // Hardware / GPU product names
  "GPU","CPU","TPU","NPU","RTX","GTX","DLSS","CUDA","VRAM","DRAM","DDR",
  "SLI","NVS","PCB","PCH","USB","HDMI","OLED","LCD","LED","SSD","HDD",
  "NVMe","ARM","ISA","ALU","FPU","HBM","HPC","DPU",
])

function linkTickers(content: string): string {
  // Split on code blocks, inline code, and existing links to preserve them
  const parts = content.split(/(```[\s\S]*?```|`[^`]+`|\[.*?\]\(.*?\))/g)
  return parts.map((part, i) => {
    if (i % 2 === 1) return part // code/link — leave untouched
    // Single pass: match (^INDEX), ^INDEX, (TICKER), or bare TICKER
    return part.replace(/\(\s*(\^[A-Z]{1,5})\s*\)|\(\s*([A-Z]{2,5})\s*\)|\^([A-Z]{1,5})\b|\b([A-Z]{2,5})\b/g, (full, parenIdx, paren, idx, bare) => {
      const ticker = parenIdx ?? paren ?? (idx ? `^${idx}` : null) ?? bare
      if (!ticker || (!parenIdx && !idx && SKIP_WORDS.has(ticker))) return full
      return `[${ticker}](#ticker-${encodeURIComponent(ticker)})`
    })
  }).join("")
}

interface Props {
  message: Message
  userEmail?: string
  onTickerClick?: (ticker: string) => void
}

function UserAvatar({ email = "" }: { email?: string }) {
  const parts = email.split("@")[0].split(/[._-]/)
  const initials = parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : (email.slice(0, 2) || "U").toUpperCase()
  return (
    <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
      style={{ backgroundColor: "var(--color-purple)", color: "white" }}>
      {initials}
    </div>
  )
}

function AIAvatar() {
  return (
    <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
      style={{ backgroundColor: "var(--color-teal)", color: "white" }}>
      AI
    </div>
  )
}

function MarkdownContent({ content, onTickerClick }: { content: string; onTickerClick?: (ticker: string) => void }) {
  const processed = onTickerClick ? linkTickers(content) : content
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold" style={{ color: "var(--text-primary)" }}>{children}</strong>,
        h1: ({ children }) => <h1 className="font-bold text-base mt-3 mb-1" style={{ color: "var(--text-primary)" }}>{children}</h1>,
        h2: ({ children }) => <h2 className="font-bold text-sm mt-3 mb-1" style={{ color: "var(--text-primary)" }}>{children}</h2>,
        h3: ({ children }) => <h3 className="font-semibold text-sm mt-2 mb-1" style={{ color: "var(--text-primary)" }}>{children}</h3>,
        ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
        code: ({ children }) => (
          <code className="px-1 py-0.5 rounded text-xs font-mono-numbers"
            style={{ backgroundColor: "var(--surface)", color: "var(--color-teal)" }}>
            {children}
          </code>
        ),
        a: ({ href, children }) => {
          if (href?.startsWith("#ticker-")) {
            const ticker = decodeURIComponent(href.slice(8))
            return (
              <button
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); onTickerClick?.(ticker) }}
                className="inline font-bold font-mono-numbers text-xs px-1.5 py-0.5 rounded cursor-pointer transition-opacity hover:opacity-75"
                style={{ color: "var(--color-teal)", backgroundColor: "rgba(29,158,117,0.12)", border: "1px solid rgba(29,158,117,0.3)" }}
              >
                {children}
              </button>
            )
          }
          return <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "var(--color-teal)", textDecoration: "underline" }}>{children}</a>
        },
        table: ({ children }) => (
          <div className="overflow-x-auto my-3 rounded-xl" style={{ border: "1px solid var(--border)" }}>
            <table className="w-full text-xs border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead style={{ backgroundColor: "var(--surface)" }}>{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left font-semibold" style={{ color: "var(--text-primary)", borderBottom: "1px solid var(--border)" }}>
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 font-mono-numbers" style={{ color: "var(--text-secondary)", borderBottom: "1px solid var(--border)" }}>
            {children}
          </td>
        ),
        tr: ({ children }) => (
          <tr className="last:border-0" style={{ borderBottom: "1px solid var(--border)" }}>
            {children}
          </tr>
        ),
        blockquote: ({ children }) => (
          <blockquote className="pl-3 my-2 italic" style={{ borderLeft: `3px solid var(--color-teal)`, color: "var(--text-secondary)" }}>
            {children}
          </blockquote>
        ),
      }}
    >
      {processed}
    </ReactMarkdown>
  )
}

export default function MessageBubble({ message, userEmail, onTickerClick }: Props) {
  const isUser = message.role === "user"

  if (isUser) {
    return (
      <div className="flex justify-end items-start gap-2 mb-5">
        <div className="max-w-[70%] px-4 py-3 rounded-2xl text-sm leading-relaxed"
          style={{ backgroundColor: "var(--color-purple)", color: "white", borderRadius: "18px 18px 4px 18px" }}>
          {message.content}
        </div>
        <UserAvatar email={userEmail} />
      </div>
    )
  }

  return (
    <div className="flex justify-start items-start gap-2 mb-5">
      <AIAvatar />
      <div className="max-w-[80%] space-y-2">

        {/* Tool cards ABOVE the text response */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <ToolResult toolCalls={message.tool_calls} onTickerClick={onTickerClick} />
        )}

        {/* Text response — skip if empty or placeholder dash */}
        {message.content.trim() && message.content.trim() !== "—" && (
          <div className="px-4 py-3 rounded-2xl text-sm"
            style={{ backgroundColor: "var(--surface-2)", color: "var(--text-secondary)", borderRadius: "18px 18px 18px 4px" }}>
            <MarkdownContent content={message.content} onTickerClick={onTickerClick} />
          </div>
        )}

        {/* Per-message token count */}
        {message.tokens_used != null && message.tokens_used > 0 && (
          <p className="text-xs font-mono-numbers pl-1" style={{ color: "var(--text-secondary)", opacity: 0.5 }}>
            {message.tokens_used.toLocaleString()} tokens
          </p>
        )}

        {/* Source indicator */}
        {(() => {
          const tools = message.tool_calls?.map(tc => tc.tool) ?? []
          const hasMarketTools = tools.some(t => ["get_stock_price","get_stock_history","get_fundamentals","compare_stocks","get_company_news","calculate_portfolio_risk"].includes(t))
          const hasRag = tools.includes("search_knowledge_base")
          const ragSources = message.sources && message.sources.length > 0
            ? [...new Set(message.sources.map(s => s.metadata.source.split("/").pop()?.replace(".pdf","") ?? ""))]
            : []

          if (!hasMarketTools && !hasRag) return null
          return (
            <div className="flex flex-wrap gap-1.5 pl-1">
              {hasMarketTools && (
                <span className="text-xs px-2.5 py-1 rounded-full font-medium"
                  style={{ color: "var(--text-secondary)", border: "1px solid var(--border)" }}>
                  Live data · Yahoo Finance
                </span>
              )}
              {hasRag && ragSources.map(src => (
                <span key={src} className="text-xs px-2.5 py-1 rounded-full font-medium"
                  style={{ color: "var(--color-teal)", border: "1px solid var(--color-teal)" }}>
                  {src}
                </span>
              ))}
            </div>
          )
        })()}
      </div>
    </div>
  )
}
