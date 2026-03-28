"use client"

import { useState, useEffect, useRef } from "react"
import MessageBubble from "@/components/MessageBubble"
import type { Message, ToolCall } from "@/lib/types"
import { sendMessage, getHistory, createSession } from "@/lib/api"
import { Send, ChevronDown, TrendingUp, FileText, BarChart2, Briefcase } from "lucide-react"
import MarketTicker from "@/components/MarketTicker"

const FEATURE_CARDS = [
  {
    icon: TrendingUp,
    title: "Live Market Data",
    examples: [
      "What is Apple's current stock price?",
      "Compare MSFT and GOOGL over 3 months",
      "Show me NVIDIA's price history for 1 year",
    ],
  },
  {
    icon: FileText,
    title: "Document Q&A",
    examples: [
      "What are NVIDIA's main risks from their 10-K?",
      "Summarise NVIDIA's revenue segments",
      "What was NVIDIA's gross margin in fiscal year 2024?",
    ],
  },
  {
    icon: BarChart2,
    title: "Fundamentals",
    examples: [
      "Show me IBM fundamentals",
      "What is Amazon's P/E ratio?",
      "Compare market caps of AAPL and MSFT",
    ],
  },
  {
    icon: Briefcase,
    title: "Portfolio",
    examples: [
      "How is my portfolio performing?",
      "Show me news for my holdings",
      "Calculate my portfolio risk",
    ],
  },
]


interface Props {
  sessionId: string | null
  userId: string
  userEmail: string
  messages: Message[]
  onMessageAdded: (msg: Message) => void
  onSessionCreated: (id: string) => void
  onTickerClick?: (ticker: string) => void
}

export default function ChatWindow({ sessionId, userId, userEmail, messages, onMessageAdded, onSessionCreated, onTickerClick }: Props) {
  const [input, setInput] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState("")
  const [statusMsg, setStatusMsg] = useState("")
  const [elapsedStatus, setElapsedStatus] = useState("")
  const [sessionTokens, setSessionTokens] = useState(0)
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const statusTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const ELAPSED_STEPS = [
    "Thinking...",
    "Analyzing your question...",
    "Fetching information...",
    "Processing data...",
    "Preparing response...",
  ]

  useEffect(() => {
    if (streaming && !streamingContent) {
      let step = 0
      setElapsedStatus(ELAPSED_STEPS[0])
      statusTimerRef.current = setInterval(() => {
        step = Math.min(step + 1, ELAPSED_STEPS.length - 1)
        setElapsedStatus(ELAPSED_STEPS[step])
      }, 2500)
    } else {
      if (statusTimerRef.current) clearInterval(statusTimerRef.current)
      setElapsedStatus("")
    }
    return () => { if (statusTimerRef.current) clearInterval(statusTimerRef.current) }
  }, [streaming, streamingContent])
  const hasSentMessage = messages.length > 0
  const toolCallCount = messages.filter(m => m.tool_calls?.length).length
  const justCreatedSession = useRef(false)

  useEffect(() => {
    if (sessionId) {
      if (justCreatedSession.current) {
        justCreatedSession.current = false
        return
      }
      getHistory(sessionId).then(msgs => {
        msgs.forEach(onMessageAdded)
        const total = msgs.reduce((sum, m) => sum + (m.tokens_used ?? 0), 0)
        setSessionTokens(total)
      })
    }
  }, [sessionId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, streamingContent])

  function handleScroll() {
    const el = scrollRef.current
    if (!el) return
    setShowScrollBtn(el.scrollHeight - el.scrollTop - el.clientHeight > 100)
  }

  function scrollToBottom() {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  async function handleSubmit(text?: string) {
    const msg = (text ?? input).trim()
    if (!msg || streaming) return
    setInput("")

    let sid = sessionId
    if (!sid) {
      sid = await createSession(userId, msg.slice(0, 50))
      justCreatedSession.current = true
      onSessionCreated(sid)
    }

    const userMsg: Message = {
      id: crypto.randomUUID(),
      session_id: sid,
      role: "user",
      content: msg,
      created_at: new Date().toISOString(),
    }
    onMessageAdded(userMsg)
    setStreaming(true)
    setStreamingContent("")
    setStatusMsg("")

    let fullContent = ""
    let finalToolCalls: ToolCall[] | undefined
    let finalTokens = 0

    await sendMessage(
      msg, sid, userId,
      (token) => { fullContent += token; setStreamingContent(fullContent) },
      (tcs, tokens) => { finalToolCalls = tcs; finalTokens = tokens },
      (err) => { fullContent = `Error: ${err}`; setStreamingContent(fullContent) },
      (status) => { setStatusMsg(status) },
      () => { fullContent = ""; setStreamingContent("") }
    )

    setSessionTokens(prev => prev + finalTokens)

    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      session_id: sid,
      role: "assistant",
      content: fullContent,
      tool_calls: finalToolCalls,
      tokens_used: finalTokens,
      created_at: new Date().toISOString(),
    }
    onMessageAdded(assistantMsg)
    setStreaming(false)
    setStreamingContent("")
    setStatusMsg("")
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      {hasSentMessage && (
        <div className="px-6 py-3 border-b flex items-center gap-3" style={{ borderColor: "var(--border)" }}>
          <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
            {messages.length} messages
          </span>
          {toolCallCount > 0 && (
            <>
              <span style={{ color: "var(--border)" }}>·</span>
              <span className="text-xs" style={{ color: "var(--color-teal)" }}>
                {toolCallCount} tool call{toolCallCount !== 1 ? "s" : ""}
              </span>
            </>
          )}
          {sessionTokens > 0 && (
            <>
              <span style={{ color: "var(--border)" }}>·</span>
              <span className="text-xs font-mono-numbers" style={{ color: "var(--text-secondary)" }}>
                {sessionTokens.toLocaleString()} tokens
              </span>
              <span className="text-xs font-mono-numbers px-1.5 py-0.5 rounded-full"
                style={{ color: "var(--color-teal)", backgroundColor: "rgba(29,158,117,0.08)" }}>
                ~${(sessionTokens * 0.00000030).toFixed(4)}
              </span>
            </>
          )}
        </div>
      )}

      {/* Messages */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-6 py-6 relative"
      >
        {messages.length === 0 && !streaming && (
          <div className="flex flex-col items-center justify-center h-full gap-6 py-8">
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-1">
                <span style={{ color: "var(--text-primary)" }}>fin</span><span style={{ color: "var(--color-teal)" }}>sight</span>
              </h2>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                Ask about stocks, annual reports, portfolio performance, and more.
              </p>
            </div>
            <MarketTicker />
            <div className="grid grid-cols-2 gap-3 w-full max-w-2xl">
              {FEATURE_CARDS.map(({ icon: Icon, title, examples }) => (
                <div
                  key={title}
                  className="rounded-xl p-4 space-y-2.5"
                  style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)" }}
                >
                  <div className="flex items-center gap-2">
                    <Icon size={14} style={{ color: "var(--color-teal)" }} />
                    <span className="text-xs font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>
                      {title.toUpperCase()}
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {examples.map(ex => (
                      <button
                        key={ex}
                        onClick={() => handleSubmit(ex)}
                        className="w-full text-left text-xs px-3 py-2 rounded-lg transition-opacity hover:opacity-75"
                        style={{ backgroundColor: "var(--surface-2)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
                      >
                        {ex}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {messages.map(m => (
          <MessageBubble key={m.id} message={m} userEmail={userEmail} onTickerClick={onTickerClick} />
        ))}

        {/* Typing / status indicator */}
        {streaming && !streamingContent && (
          <div className="flex justify-start items-start gap-2 mb-5">
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{ backgroundColor: "var(--color-teal)", color: "white" }}>AI</div>
            <div className="px-4 py-3 rounded-2xl flex items-center gap-2"
              style={{ backgroundColor: "var(--surface-2)", borderRadius: "18px 18px 18px 4px" }}>
              <div className="flex gap-1 items-center">
                {[0, 1, 2].map(i => (
                  <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce"
                    style={{ backgroundColor: "var(--color-teal)", animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
              <span className="text-xs italic" style={{ color: "var(--color-teal)" }}>
                {statusMsg || elapsedStatus}
              </span>
            </div>
          </div>
        )}

        {/* Streaming bubble */}
        {streaming && streamingContent && (
          <div className="flex justify-start items-start gap-2 mb-5">
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{ backgroundColor: "var(--color-teal)", color: "white" }}>AI</div>
            <div className="max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap"
              style={{ backgroundColor: "var(--surface-2)", color: "var(--text-primary)", borderRadius: "18px 18px 18px 4px" }}>
              {streamingContent}
              <span className="inline-block w-1.5 h-3.5 ml-0.5 animate-pulse rounded-sm" style={{ backgroundColor: "var(--color-teal)" }} />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Scroll to bottom */}
      {showScrollBtn && (
        <div className="relative">
          <button
            onClick={scrollToBottom}
            className="absolute bottom-2 left-1/2 -translate-x-1/2 p-1.5 rounded-full shadow-lg"
            style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
          >
            <ChevronDown size={16} />
          </button>
        </div>
      )}


      {/* Input */}
      <div className="px-4 pb-4">
        <div className="flex items-end gap-2 rounded-2xl px-4 py-3"
          style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit() } }}
            placeholder="Ask about stocks, filings, market trends..."
            rows={1}
            className="flex-1 bg-transparent text-sm resize-none outline-none"
            style={{ color: "var(--text-primary)", maxHeight: 120 }}
          />
          <button
            onClick={() => handleSubmit()}
            disabled={!input.trim() || streaming}
            className="p-1.5 rounded-lg transition-opacity disabled:opacity-30"
            style={{ backgroundColor: "var(--color-teal)", color: "white" }}
          >
            <Send size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}
