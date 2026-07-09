'use client'

import { useState } from 'react'

type HtmlFile = {
  path: string
  name: string
  size: number
  companions: string[]
}

export function HtmlSelectPanel() {
  const [dir, setDir] = useState('')
  const [files, setFiles] = useState<HtmlFile[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [targetType, setTargetType] = useState('page')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ session_id?: string; package?: string; next?: string[] } | null>(null)

  async function listFiles() {
    setLoading(true)
    setError(null)
    setMessage(null)
    setResult(null)
    try {
      const res = await fetch(`/api/intake?dir=${encodeURIComponent(dir)}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || '一覧取得に失敗しました')
      setFiles(data.files || [])
      setSelected(new Set())
      setMessage(`${(data.files || []).length} 件の HTML を検出しました`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setFiles([])
    } finally {
      setLoading(false)
    }
  }

  function toggle(path: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  function selectAll() {
    setSelected(new Set(files.map((f) => f.path)))
  }

  async function startPipeline() {
    if (!selected.size) {
      setError('HTML を1つ以上選択してください')
      return
    }
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      const res = await fetch('/api/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_dir: dir,
          select: Array.from(selected),
          target_type: targetType,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'パイプライン開始に失敗しました')
      setResult(data)
      setMessage(`セッション ${data.session_id} を準備しました`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="select-panel">
      <div className="select-row">
        <label htmlFor="html-dir">HTML フォルダのパス</label>
        <div className="select-controls">
          <input
            id="html-dir"
            type="text"
            value={dir}
            onChange={(e) => setDir(e.target.value)}
            placeholder="C:\path\to\html-folder"
            disabled={loading}
          />
          <button type="button" className="btn" onClick={listFiles} disabled={loading || !dir.trim()}>
            一覧
          </button>
        </div>
      </div>

      <div className="select-row">
        <label htmlFor="target-type">ターゲット種別</label>
        <select
          id="target-type"
          value={targetType}
          onChange={(e) => setTargetType(e.target.value)}
          disabled={loading}
        >
          <option value="page">page</option>
          <option value="block">block</option>
          <option value="theme">theme</option>
          <option value="template-part">template-part</option>
          <option value="custom-css">custom-css</option>
        </select>
      </div>

      {files.length > 0 && (
        <>
          <div className="select-toolbar">
            <span>{selected.size} / {files.length} 選択</span>
            <button type="button" className="btn-ghost" onClick={selectAll} disabled={loading}>
              すべて選択
            </button>
            <button type="button" className="btn-ghost" onClick={() => setSelected(new Set())} disabled={loading}>
              クリア
            </button>
          </div>
          <ul className="file-list" role="listbox" aria-label="HTML ファイル">
            {files.map((f) => {
              const checked = selected.has(f.path)
              const comps = f.companions.map((c) => c.split(/[/\\]/).pop()).join(', ') || 'なし'
              return (
                <li key={f.path}>
                  <label className={checked ? 'is-checked' : undefined}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(f.path)}
                      disabled={loading}
                    />
                    <span className="file-meta">
                      <strong>{f.path}</strong>
                      <small>{(f.size / 1024).toFixed(1)} KB · 関連: {comps}</small>
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
          <button
            type="button"
            className="btn btn-primary"
            onClick={startPipeline}
            disabled={loading || selected.size === 0}
          >
            {loading ? '処理中…' : '選択してパイプライン開始'}
          </button>
        </>
      )}

      {message && <p className="select-msg ok">{message}</p>}
      {error && <p className="select-msg err">{error}</p>}

      {result && (
        <div className="select-result">
          <p>
            パッケージ: <code>{result.package}</code>
          </p>
          <p>
            セッション: <code>{result.session_id}</code>
          </p>
          {result.next && (
            <ol>
              {result.next.map((step) => (
                <li key={step}>
                  <code>{step}</code>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  )
}
