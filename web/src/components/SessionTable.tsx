'use client'

import { useEffect, useState } from 'react'

type Session = {
  id: string
  status: string
  agent: string
  target: string
  staging_url?: string | null
  updated_at?: string | null
}

function badgeClass(status: string) {
  if (status.includes('deployed') || status === 'converted' || status === 'validated') {
    return 'badge badge-ok'
  }
  if (status.includes('pending') || status.includes('failed')) return 'badge badge-warn'
  return 'badge badge-muted'
}

export function SessionTable() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [source, setSource] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/sessions')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = (await res.json()) as { sessions: Session[]; source?: string }
        if (!cancelled) {
          setSessions(data.sessions)
          setSource(data.source || '')
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : '読み込み失敗')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <p className="empty">セッションを読み込み中…</p>
  if (error) return <p className="empty">取得エラー: {error}</p>
  if (!sessions.length) {
    return (
      <p className="empty">
        セッションがありません。ローカルで <code>python wpaipublish.py db sync</code> を実行し、
        Railway の <code>DATABASE_URL</code> を設定してください。
      </p>
    )
  }

  return (
    <>
      {source ? (
        <p style={{ margin: '0 0 0.75rem', fontSize: '0.78rem', color: 'var(--muted)' }}>
          データソース: {source === 'postgres' ? 'PostgreSQL' : 'ローカル filesystem'}
        </p>
      ) : null}
      <table className="table">
        <thead>
          <tr>
            <th>Session</th>
            <th>Status</th>
            <th>Agent</th>
            <th>Target</th>
            <th>Staging</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.id}>
              <td>{s.id}</td>
              <td>
                <span className={badgeClass(s.status)}>{s.status}</span>
              </td>
              <td>{s.agent || '-'}</td>
              <td>{s.target}</td>
              <td>
                {s.staging_url ? (
                  <a href={s.staging_url} target="_blank" rel="noreferrer">
                    開く
                  </a>
                ) : (
                  '-'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
