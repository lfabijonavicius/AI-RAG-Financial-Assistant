"use client"

import { useState, useEffect } from "react"
import Sidebar from "@/components/Sidebar"
import ChatWindow from "@/components/ChatWindow"
import { RightPanel } from "@/components/right-panel/RightPanel"
import type { Message, ChatSession, ToolCall, PinnedTicker } from "@/lib/types"
import { createClient } from "@/lib/supabase"
import { createSession } from "@/lib/api"

interface Props {
  userId: string
  userEmail: string
}

export default function ChatLayout({ userId, userEmail }: Props) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [latestToolCalls, setLatestToolCalls] = useState<ToolCall[]>([])
  const [pinnedTicker, setPinnedTicker] = useState<PinnedTicker | null>(null)
  const [pinnedLoading, setPinnedLoading] = useState(false)

  useEffect(() => {
    loadSessions()
  }, [])

  async function loadSessions() {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/sessions/${userId}`)
    if (res.ok) {
      const data = await res.json()
      setSessions(data.sessions ?? [])
    }
  }

  function handleNewSession() {
    setActiveSessionId(null)
    setMessages([])
    setLatestToolCalls([])
    setPinnedTicker(null)
  }

  function handleMessageAdded(msg: Message) {
    setMessages(prev => [...prev, msg])
    if (msg.tool_calls?.length) setLatestToolCalls(msg.tool_calls)
  }

  async function handleTickerClick(ticker: string) {
    setPinnedLoading(true)
    setPinnedTicker(null)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/ticker/${encodeURIComponent(ticker)}`)
      if (res.ok) {
        const data = await res.json()
        setPinnedTicker(data as PinnedTicker)
      }
    } finally {
      setPinnedLoading(false)
    }
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: "var(--background)" }}>
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        userId={userId}
        userEmail={userEmail}
        onSelectSession={(id) => { setActiveSessionId(id); setMessages([]) }}
        onNewSession={handleNewSession}
      />
      <div className="flex-1 min-w-0">
        <ChatWindow
          sessionId={activeSessionId}
          userId={userId}
          userEmail={userEmail}
          messages={messages}
          onMessageAdded={handleMessageAdded}
          onSessionCreated={(id) => { setActiveSessionId(id); loadSessions() }}
          onTickerClick={handleTickerClick}
        />
      </div>
      <div className="hidden lg:block w-[280px] shrink-0">
        <RightPanel
          toolCalls={latestToolCalls}
          messages={messages}
          userId={userId}
          pinnedTicker={pinnedTicker}
          pinnedLoading={pinnedLoading}
          onClearPinned={() => setPinnedTicker(null)}
        />
      </div>
    </div>
  )
}
