'use client'

import { useState } from 'react'

type Props = {
  sessionId: string
  className?: string
  label?: string
  disabled?: boolean
  /** アンカー直リンクも出す（見つかりやすくする） */
  showDirectLink?: boolean
}

export function SessionDownloadButton({
  sessionId,
  className = 'btn btn-primary',
  label = 'セッションをダウンロード',
  disabled = false,
  showDirectLink = true,
}: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const href = sessionId ? `/api/sessions/${encodeURIComponent(sessionId)}/download` : '#'

  async function download() {
    if (!sessionId || busy) return
    setBusy(true)
    setError('')
    try {
      const res = await fetch(href, {
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

  if (!sessionId) return null

  return (
    <div
      className="session-download"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
        margin: '0.75rem 0',
        padding: '0.85rem 1rem',
        borderRadius: 12,
        border: '2px solid var(--accent)',
        background: '#fff',
      }}
    >
      <strong style={{ fontSize: '0.95rem' }}>成果物ダウンロード</strong>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
        <button
          type="button"
          className={className}
          disabled={disabled || busy}
          onClick={() => void download()}
        >
          {busy ? 'ZIP 作成中…' : label}
        </button>
        {showDirectLink ? (
          <a
            href={href}
            download={`wpai-session-${sessionId}.zip`}
            style={{ fontWeight: 700, textDecoration: 'underline' }}
          >
            ZIPリンクを開く
          </a>
        ) : null}
      </div>
      <small style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>
        セッション <code>{sessionId}</code> の output / incoming を ZIP で取得します。
      </small>
      {error ? (
        <small className="select-msg err" style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
          {error}
        </small>
      ) : null}
    </div>
  )
}
