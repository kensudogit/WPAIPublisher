'use client'

import { useState } from 'react'

type Props = {
  sessionId: string
  className?: string
  label?: string
  disabled?: boolean
}

export function SessionDownloadButton({
  sessionId,
  className = 'btn',
  label = 'セッションをダウンロード',
  disabled = false,
}: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function download() {
    if (!sessionId || busy) return
    setBusy(true)
    setError('')
    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/download`, {
        method: 'GET',
        cache: 'no-store',
      })
      if (!res.ok) {
        let msg = `ダウンロード失敗 (${res.status})`
        try {
          const data = (await res.json()) as { error?: string }
          if (data.error) msg = data.error
        } catch {
          // ignore
        }
        throw new Error(msg)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `wpai-session-${sessionId}.zip`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <span style={{ display: 'inline-flex', flexDirection: 'column', gap: '0.25rem' }}>
      <button
        type="button"
        className={className}
        disabled={disabled || busy || !sessionId}
        onClick={() => void download()}
      >
        {busy ? 'ZIP 作成中…' : label}
      </button>
      {error ? (
        <small className="select-msg err" style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
          {error}
        </small>
      ) : null}
    </span>
  )
}
