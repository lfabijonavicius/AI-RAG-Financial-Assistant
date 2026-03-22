"use client"

import type { Message } from "@/lib/types"
import { Download, Copy, Check } from "lucide-react"
import { useState } from "react"

interface Props {
  messages: Message[]
}

export default function ExportTab({ messages }: Props) {
  const [copied, setCopied] = useState(false)

  function downloadJSON() {
    const blob = new Blob([JSON.stringify(messages, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a"); a.href = url; a.download = "chat-export.json"; a.click()
    URL.revokeObjectURL(url)
  }

  function downloadCSV() {
    const rows = [["timestamp", "role", "content"]]
    messages.forEach(m => rows.push([m.created_at, m.role, `"${m.content.replace(/"/g, '""')}"`]))
    const blob = new Blob([rows.map(r => r.join(",")).join("\n")], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a"); a.href = url; a.download = "chat-export.csv"; a.click()
    URL.revokeObjectURL(url)
  }

  async function copyToClipboard() {
    const text = messages.map(m => `[${m.role.toUpperCase()}] ${m.content}`).join("\n\n")
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="px-4 py-4 space-y-3">
      <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{messages.length} messages in this session</p>
      {[
        { label: "Download JSON", icon: <Download size={13} />, action: downloadJSON },
        { label: "Download CSV", icon: <Download size={13} />, action: downloadCSV },
        { label: copied ? "Copied!" : "Copy to clipboard", icon: copied ? <Check size={13} /> : <Copy size={13} />, action: copyToClipboard },
      ].map(({ label, icon, action }) => (
        <button
          key={label}
          onClick={action}
          disabled={messages.length === 0}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-opacity disabled:opacity-30"
          style={{ backgroundColor: "var(--surface-2)", color: "var(--text-primary)", border: "1px solid var(--border)" }}
        >
          {icon} {label}
        </button>
      ))}
    </div>
  )
}
