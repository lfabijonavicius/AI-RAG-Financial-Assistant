"use client"

import { useState, useEffect } from "react"
import DetailsTab from "@/components/right-panel/DetailsTab"
import PortfolioTab from "@/components/right-panel/PortfolioTab"
import ExportTab from "@/components/right-panel/ExportTab"
import DocsTab from "@/components/right-panel/DocsTab"
import type { ToolCall, Message, PinnedTicker } from "@/lib/types"

const TABS = ["Details", "Portfolio", "Docs", "Export"] as const
type Tab = typeof TABS[number]

interface Props {
  toolCalls: ToolCall[]
  messages: Message[]
  userId: string
  pinnedTicker?: PinnedTicker | null
  pinnedLoading?: boolean
  onClearPinned?: () => void
}

export function RightPanel({ toolCalls, messages, userId, pinnedTicker, pinnedLoading, onClearPinned }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("Details")

  // Auto-switch to Details tab when a ticker is pinned
  useEffect(() => {
    if (pinnedTicker || pinnedLoading) setActiveTab("Details")
  }, [pinnedTicker, pinnedLoading])

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: "var(--surface)", borderLeft: "1px solid var(--border)" }}>
      {/* Tab bar */}
      <div className="flex border-b" style={{ borderColor: "var(--border)" }}>
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="flex-1 py-3 text-xs font-medium transition-colors"
            style={{
              color: activeTab === tab ? "var(--color-teal)" : "var(--text-secondary)",
              borderBottom: activeTab === tab ? "2px solid var(--color-teal)" : "2px solid transparent",
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "Details" && <DetailsTab toolCalls={toolCalls} pinnedTicker={pinnedTicker} pinnedLoading={pinnedLoading} onClearPinned={onClearPinned} />}
        {activeTab === "Portfolio" && <PortfolioTab userId={userId} />}
        {activeTab === "Docs" && <DocsTab />}
        {activeTab === "Export" && <ExportTab messages={messages} />}
      </div>
    </div>
  )
}
