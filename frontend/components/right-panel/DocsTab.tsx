"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Upload, Trash2, FileText, RefreshCw } from "lucide-react"

interface DocFile {
  name: string
  size: number
}

const API = process.env.NEXT_PUBLIC_API_URL

function fmtSize(bytes: number) {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${bytes} B`
}

export default function DocsTab() {
  const [files, setFiles] = useState<DocFile[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState("")
  const [error, setError] = useState("")
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/documents`)
      if (res.ok) {
        const data = await res.json()
        setFiles(data.files ?? [])
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleUpload(file: File) {
    setError("")
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are accepted.")
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("File too large. Maximum size is 10MB.")
      return
    }

    setUploading(true)
    setUploadStatus("Uploading...")
    const form = new FormData()
    form.append("file", file)

    try {
      const res = await fetch(`${API}/documents/upload`, { method: "POST", body: form })
      if (res.ok) {
        const data = await res.json()
        setUploadStatus(`Done — ${data.chunks_indexed} chunks indexed`)
        await load()
        setTimeout(() => setUploadStatus(""), 4000)
      } else {
        const err = await res.json()
        setError(err.detail ?? "Upload failed.")
      }
    } catch {
      setError("Upload failed. Check your connection.")
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(filename: string) {
    await fetch(`${API}/documents/${encodeURIComponent(filename)}`, { method: "DELETE" })
    await load()
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }

  return (
    <div className="px-4 py-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold tracking-wider" style={{ color: "var(--color-teal)" }}>● KNOWLEDGE BASE</p>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono-numbers" style={{ color: files.length >= 10 ? "#ef4444" : "var(--text-secondary)" }}>
            {files.length} / 10
          </span>
          <button onClick={load} disabled={loading} className="opacity-50 hover:opacity-100 transition-opacity">
            <RefreshCw size={12} style={{ color: "var(--text-secondary)" }} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Drop zone */}
      {files.length >= 10 ? (
        <div className="rounded-xl p-5 flex flex-col items-center justify-center gap-2"
          style={{ border: "2px dashed var(--border)", backgroundColor: "var(--surface-2)" }}>
          <Upload size={20} style={{ color: "var(--text-secondary)" }} />
          <p className="text-xs font-medium text-center" style={{ color: "#ef4444" }}>
            Document limit reached (10 / 10)
          </p>
          <p className="text-xs text-center" style={{ color: "var(--text-secondary)" }}>
            Delete a document to upload a new one
          </p>
        </div>
      ) : (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => !uploading && inputRef.current?.click()}
          className="rounded-xl p-5 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors"
          style={{
            border: `2px dashed ${dragging ? "var(--color-teal)" : "var(--border)"}`,
            backgroundColor: dragging ? "rgba(29,158,117,0.05)" : "var(--surface-2)",
          }}
        >
          <Upload size={20} style={{ color: uploading ? "var(--text-secondary)" : "var(--color-teal)" }} />
          {uploading ? (
            <p className="text-xs text-center" style={{ color: "var(--text-secondary)" }}>
              {uploadStatus || "Processing…"}
            </p>
          ) : (
            <>
              <p className="text-xs font-medium text-center" style={{ color: "var(--text-primary)" }}>
                Drop a PDF or click to upload
              </p>
              <p className="text-xs text-center" style={{ color: "var(--text-secondary)" }}>
                Annual reports, 10-Ks, research reports · max 10MB
              </p>
            </>
          )}
          <input ref={inputRef} type="file" accept=".pdf" className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleUpload(f); e.target.value = "" }} />
        </div>
      )}

      {uploadStatus && !uploading && (
        <p className="text-xs text-center" style={{ color: "var(--color-teal)" }}>{uploadStatus}</p>
      )}
      {error && (
        <p className="text-xs text-center" style={{ color: "#ef4444" }}>{error}</p>
      )}

      {/* File list */}
      {loading ? (
        <div className="flex justify-center py-4">
          <div className="flex gap-1">
            {[0,1,2].map(i => (
              <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce"
                style={{ backgroundColor: "var(--color-teal)", animationDelay: `${i * 0.15}s` }} />
            ))}
          </div>
        </div>
      ) : files.length === 0 ? (
        <p className="text-xs text-center py-2" style={{ color: "var(--text-secondary)" }}>
          No documents uploaded yet.
        </p>
      ) : (
        <div className="space-y-2">
          {files.map(f => (
            <div key={f.name} className="flex items-center gap-2 px-3 py-2 rounded-xl"
              style={{ backgroundColor: "var(--surface-2)", border: "1px solid var(--border)" }}>
              <FileText size={13} style={{ color: "var(--color-teal)", flexShrink: 0 }} />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>
                  {f.name.replace(/_/g, " ")}
                </p>
                {f.size > 0 && (
                  <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{fmtSize(f.size)}</p>
                )}
              </div>
              <button onClick={() => handleDelete(f.name)}
                className="opacity-30 hover:opacity-80 transition-opacity shrink-0">
                <Trash2 size={13} style={{ color: "var(--text-secondary)" }} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
