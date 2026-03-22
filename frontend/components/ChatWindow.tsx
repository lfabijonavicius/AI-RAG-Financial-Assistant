"use client"

import { useState, useEffect, useRef } from "react"
import MessageBubble from "@/components/MessageBubble"
import SuggestionPills from "@/components/SuggestionPills"
import type { Message, ToolCall } from "@/lib/types"
import { sendMessage, getHistory, createSession } from "@/lib/api"
import { Send, ChevronDown } from "lucide-react"

const SUGGESTIONS = [
  "What is Apple's current stock price?",
  "Compare MSFT and GOOGL over 3 months",
  "What are Tesla's main risks from their 10-K?",
  "Show me IBM fundamentals",
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

  useEffect(() => {
    if (sessionId) {
      getHistory(sessionId).then(msgs => msgs.forEach(onMessageAdded))
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

    await sendMessage(
      msg, sid, userId,
      (token) => { fullContent += token; setStreamingContent(fullContent) },
      (tcs) => { finalToolCalls = tcs },
      (err) => { fullContent = `Error: ${err}`; setStreamingContent(fullContent) },
      (status) => { setStatusMsg(status) }
    )

    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      session_id: sid,
      role: "assistant",
      content: fullContent,
      tool_calls: finalToolCalls,
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
        </div>
      )}

      {/* Messages */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-6 py-6 relative"
      >
        {messages.length === 0 && !streaming && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <h2 className="text-xl font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
                Financial Research Assistant
              </h2>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                Ask about stocks, annual reports, market trends, and more.
              </p>
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

      {/* Suggestion pills */}
      {!hasSentMessage && (
        <SuggestionPills pills={SUGGESTIONS} onSelect={(p) => handleSubmit(p)} />
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
