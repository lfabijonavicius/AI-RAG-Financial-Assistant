"use client"

import type { Source } from "@/lib/types"

interface Props {
  sources: Source[]
}

export default function SourcesTab({ sources }: Props) {
  if (!sources.length) {
    return (
      <p className="text-xs px-4 py-6 text-center" style={{ color: "var(--text-secondary)" }}>
        No sources yet. Ask a question about the knowledge base to see citations.
      </p>
    )
  }

  return (
    <div className="px-4 py-4 space-y-2">
      <p className="text-xs font-semibold tracking-wider mb-3" style={{ color: "var(--text-secondary)" }}>
        RAG SOURCES USED
      </p>
      {sources.map((s, i) => (
        <div key={i} className="flex gap-3 items-start rounded-xl p-3"
          style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}>
          <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
            style={{ backgroundColor: "var(--surface)", color: "var(--color-teal)", border: "1px solid var(--color-teal)" }}>
            {i + 1}
          </span>
          <div className="min-w-0">
            <p className="text-xs leading-relaxed line-clamp-2" style={{ color: "var(--text-secondary)" }}>
              {s.content.slice(0, 120)}…
            </p>
            <p className="text-xs mt-1 font-medium truncate" style={{ color: "var(--text-secondary)" }}>
              {s.metadata.source.split("/").pop()?.replace(".pdf", "")}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
