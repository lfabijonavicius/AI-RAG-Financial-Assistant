export interface Source {
  content: string
  metadata: { source: string; similarity?: number }
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
  result?: Record<string, unknown> | null
}

export interface Message {
  id: string
  session_id: string
  role: "user" | "assistant"
  content: string
  sources?: Source[]
  tool_calls?: ToolCall[]
  tokens_used?: number
  created_at: string
}

export interface ChatSession {
  id: string
  user_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface PinnedTicker {
  ticker: string
  name?: string
  price?: number
  pe_ratio?: number
  forward_pe?: number
  market_cap?: number
  "52w_high"?: number
  "52w_low"?: number
  dividend_yield?: number
  eps?: number
  total_return_pct?: number
  history: number[]
}

export interface HealthResponse {
  status: string
  supabase_connected: boolean
  vectordb_ready: boolean
}

export interface StreamChunk {
  token?: string
  status?: string
  sources?: Source[]
  tool_calls?: ToolCall[]
  tokens_used?: number
  error?: string
}
