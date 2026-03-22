import type { StreamChunk, Message } from "@/lib/types"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function sendMessage(
  message: string,
  sessionId: string,
  userId: string,
  onToken: (token: string) => void,
  onDone: (toolCalls: StreamChunk["tool_calls"]) => void,
  onError: (err: string) => void,
  onStatus?: (status: string) => void
): Promise<void> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, user_id: userId }),
  })

  if (!res.ok || !res.body) {
    onError(`Request failed: ${res.status}`)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const lines = decoder.decode(value).split("\n")
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue
      const raw = line.slice(6).trim()
      if (raw === "[DONE]") { continue }
      try {
        const chunk: StreamChunk = JSON.parse(raw)
        if (chunk.error) { onError(chunk.error); continue }
        if (chunk.status) { onStatus?.(chunk.status); continue }
        if (chunk.token) onToken(chunk.token)
        if (chunk.tool_calls !== undefined) onDone(chunk.tool_calls)
      } catch { /* ignore malformed lines */ }
    }
  }
}

export async function getHistory(sessionId: string): Promise<Message[]> {
  const res = await fetch(`${BASE}/history/${sessionId}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.messages ?? []
}

export async function createSession(userId: string, title = "New Chat"): Promise<string> {
  const res = await fetch(`${BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, title }),
  })
  const data = await res.json()
  return data.session_id
}
