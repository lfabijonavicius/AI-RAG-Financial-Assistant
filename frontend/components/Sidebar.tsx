"use client"

import { createClient } from "@/lib/supabase"
import { useRouter } from "next/navigation"
import type { ChatSession } from "@/lib/types"
import { Plus, LogOut } from "lucide-react"

interface Props {
  sessions: ChatSession[]
  activeSessionId: string | null
  userId: string
  userEmail: string
  onSelectSession: (id: string) => void
  onNewSession: () => void
}

function Initials({ email }: { email: string }) {
  const parts = email.split("@")[0].split(/[._-]/)
  const initials = parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : email.slice(0, 2).toUpperCase()
  return (
    <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
      style={{ backgroundColor: "var(--color-purple)", color: "white" }}>
      {initials}
    </div>
  )
}

export default function Sidebar({ sessions, activeSessionId, userEmail, onSelectSession, onNewSession }: Props) {
  const supabase = createClient()
  const router = useRouter()

  async function handleLogout() {
    await supabase.auth.signOut()
    router.push("/login")
  }

  const recentSessions = sessions.filter(s => s.id !== activeSessionId)
  const activeSession = sessions.find(s => s.id === activeSessionId)

  return (
    <div className="w-[220px] shrink-0 flex flex-col h-full" style={{ backgroundColor: "var(--surface)", borderRight: "1px solid var(--border)" }}>
      {/* Brand */}
      <div className="px-4 pt-4 pb-3 border-b" style={{ borderColor: "var(--border)" }}>
        <p className="text-xl font-bold">
          <span style={{ color: "var(--text-primary)" }}>fin</span><span style={{ color: "var(--color-teal)" }}>sight</span>
        </p>
      </div>

      {/* User */}
      <div className="px-4 py-4 flex items-center gap-3 border-b" style={{ borderColor: "var(--border)" }}>
        <Initials email={userEmail} />
        <div className="min-w-0">
          <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
            {userEmail.split("@")[0]}
          </p>
          <p className="text-xs truncate" style={{ color: "var(--text-secondary)" }}>{userEmail}</p>
        </div>
      </div>

      {/* New chat button */}
      <div className="p-3">
        <button
          onClick={onNewSession}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80"
          style={{ backgroundColor: "var(--color-teal)", color: "white" }}
        >
          <Plus size={14} /> New Chat
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 space-y-4">
        {/* Active session */}
        {activeSession && (
          <div>
            <p className="text-xs font-semibold px-2 py-1 tracking-wider" style={{ color: "var(--text-secondary)" }}>NEW CHAT</p>
            <button
              onClick={() => onSelectSession(activeSession.id)}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left"
              style={{ backgroundColor: "var(--surface-2)", color: "var(--text-primary)" }}
            >
              <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: "var(--color-teal)" }} />
              <span className="truncate">{activeSession.title}</span>
            </button>
          </div>
        )}

        {/* Recent sessions */}
        {recentSessions.length > 0 && (
          <div>
            <p className="text-xs font-semibold px-2 py-1 tracking-wider" style={{ color: "var(--text-secondary)" }}>RECENT</p>
            <div className="space-y-0.5">
              {recentSessions.map(s => (
                <button
                  key={s.id}
                  onClick={() => onSelectSession(s.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors hover:opacity-80"
                  style={{ color: "var(--text-secondary)" }}
                >
                  <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: "var(--border)" }} />
                  <span className="truncate">{s.title}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {sessions.length === 0 && (
          <p className="text-xs px-3 py-2" style={{ color: "var(--text-secondary)" }}>No sessions yet</p>
        )}
      </div>

      {/* Logout */}
      <div className="p-3 border-t" style={{ borderColor: "var(--border)" }}>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-opacity hover:opacity-75"
          style={{ color: "#ef4444", backgroundColor: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}
        >
          <LogOut size={14} /> Logout
        </button>
      </div>
    </div>
  )
}
