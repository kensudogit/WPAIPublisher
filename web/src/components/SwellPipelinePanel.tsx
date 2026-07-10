'use client'

import { useState } from 'react'

type PipelineResult = {
  session_id?: string
  ok?: boolean
  steps?: { step: string; ok: boolean }[]
  report?: string
  error?: string
}

type ReportPayload = {
  markdown?: string | null
  report?: {
    overall?: string
    status?: string
    conversion?: { blocks?: string[]; theme_slug?: string }
    visual?: { passed?: boolean }
    structure?: { component_count?: number }
  } | null
  structure?: { components?: { id: string; kind: string; swell_target: string }[] } | null
  visual?: { passed?: boolean; results?: { viewport: string; passed: boolean; diffPercent?: number }[] } | null
}

export function SwellPipelinePanel() {
  const [dir, setDir] = useState('')
  const [select, setSelect] = useState('hero.html')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PipelineResult | null>(null)
  const [report, setReport] = useState<ReportPayload | null>(null)

  async function runPipeline() {
    setRunning(true)
    setError('')
    setResult(null)
    setReport(null)
    try {
      const selects = select
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      const res = await fetch('/api/swell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_dir: dir,
          select: selects,
          visual_update: true,
          skip_git: true,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'pipeline failed')
      setResult(data)
      if (data.session_id) {
        const r = await fetch(`/api/swell?session=${encodeURIComponent(data.session_id)}`)
        if (r.ok) setReport(await r.json())
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
    }
  }

  async function loadReport(session: string) {
    setError('')
    const r = await fetch(`/api/swell?session=${encodeURIComponent(session)}`)
    if (!r.ok) {
      setError('レポートが見つかりません')
      return
    }
    setReport(await r.json())
  }

  return (
    <div className="select-panel">
      <div className="select-row">
        <label htmlFor="swell-dir">HTML フォルダ</label>
        <input
          id="swell-dir"
          value={dir}
          onChange={(e) => setDir(e.target.value)}
          placeholder="C:\path\to\html-folder"
          disabled={running}
        />
      </div>
      <div className="select-row">
        <label htmlFor="swell-select">選択 HTML（カンマ区切り）</label>
        <input
          id="swell-select"
          value={select}
          onChange={(e) => setSelect(e.target.value)}
          placeholder="hero.html, pages/about.html"
          disabled={running}
        />
      </div>
      <button
        type="button"
        className="btn btn-primary"
        onClick={runPipeline}
        disabled={running || !dir.trim() || !select.trim()}
      >
        {running ? '実行中…' : 'SWELL パイプライン実行'}
      </button>
      <p className="page-lead" style={{ margin: 0 }}>
        解析 → SWELL 変換 → validate → deploy → visual（ベースライン更新）→ レポート。Git push は CLI で実行してください。
      </p>

      {error && <p className="select-msg err">{error}</p>}

      {result && (
        <div className="select-result">
          <p>
            セッション: <code>{result.session_id}</code> · {result.ok ? 'OK' : 'NG'}
          </p>
          <ul>
            {(result.steps || []).map((s) => (
              <li key={s.step}>
                [{s.ok ? 'OK' : 'NG'}] {s.step}
              </li>
            ))}
          </ul>
          {result.session_id && (
            <button type="button" className="btn" onClick={() => void loadReport(result.session_id!)}>
              レポート再読込
            </button>
          )}
        </div>
      )}

      {report?.report && (
        <div className="panel" style={{ marginTop: '0.5rem' }}>
          <div className="panel-head">
            <h2>変更レポート</h2>
          </div>
          <div className="panel-body">
            <div className="test-summary">
              <span className={report.report.overall === 'passed' ? 'badge badge-ok' : 'badge badge-warn'}>
                {report.report.overall}
              </span>
              <span>{report.report.conversion?.theme_slug}</span>
              <span>blocks: {(report.report.conversion?.blocks || []).join(', ') || '-'}</span>
              <span>visual: {String(report.visual?.passed ?? report.report.visual?.passed)}</span>
            </div>
            {report.structure?.components && (
              <table className="table" style={{ marginTop: '1rem' }}>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Kind</th>
                    <th>SWELL</th>
                  </tr>
                </thead>
                <tbody>
                  {report.structure.components.slice(0, 20).map((c) => (
                    <tr key={c.id}>
                      <td>{c.id}</td>
                      <td>{c.kind}</td>
                      <td>{c.swell_target}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {report.markdown && (
              <pre className="test-msg" style={{ maxHeight: 320, marginTop: '1rem' }}>
                {report.markdown}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
