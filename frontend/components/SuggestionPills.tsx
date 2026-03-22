"use client"

import { ArrowUpRight } from "lucide-react"

interface Props {
  pills: string[]
  onSelect: (pill: string) => void
}

export default function SuggestionPills({ pills, onSelect }: Props) {
  return (
    <div className="flex flex-wrap gap-2 px-4 pb-3 justify-center">
      {pills.map(pill => (
        <button
          key={pill}
          onClick={() => onSelect(pill)}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-colors hover:opacity-80"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--surface-2)",
            color: "var(--text-secondary)",
          }}
        >
          {pill}
          <ArrowUpRight size={11} style={{ color: "var(--color-teal)" }} />
        </button>
      ))}
    </div>
  )
}
