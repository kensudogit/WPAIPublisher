'use client'

import { useRef, useState } from 'react'

type PipelineResult = {
  session_id?: string
  ok?: boolean
  steps?: { step: string; ok: boolean }[]
  report?: string
  error?: string
  source_dir?: string
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
  const fileRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<FileList | null>(null)
  const [select, setSelect] = useState('**/*.html')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PipelineResult | null>(null)
  const [report, setReport] = useState<ReportPayload | null>(null)

  function fileSummary(): string {
    if (!files?.length) return '未選択'
    const names = Array.from(files).map((f) => f.name)
    const htmlCount = names.filter((n) => n.toLowerCase().endsWith('.html')).length
    return `${files.length} ファイル（HTML ${htmlCount}）`
  }

  async function runWithFormData(form: FormData) {
    setRunning(true)
    setError('')
    setResult(null)
    setReport(null)
    try {
      const res = await fetch('/api/swell', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'pipeline failed')
      setResult(data)
      if (data.ok === false && data.error) setError(String(data.error))
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

  async function runUpload() {
    if (!files?.length) {
      setError('HTML ファイル（フォルダ）を選択してください。Railway では C:\\... のパスは使えません。')
      return
    }
    const form = new FormData()
    Array.from(files).forEach((f) => form.append('files', f))
    form.set('select', select.trim() || '**/*.html')
    form.set('visual_update', 'true')
    form.set('skip_git', 'true')
    await runWithFormData(form)
  }

  async function runSample() {
    setRunning(true)
    setError('')
    setResult(null)
    setReport(null)
    try {
      const res = await fetch('/api/swell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          use_sample: true,
          select: ['**/*.html'],
          visual_update: true,
          skip_git: true,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'pipeline failed')
      setResult(data)
      if (data.ok === false && data.error) setError(String(data.error))
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
      <p className="page-lead" style={{ margin: 0, fontSize: '0.9rem' }}>
        Railway（クラウド）では PC の <code>C:\test</code> などローカルパスは使えません。HTML
        フォルダをアップロードするか、サンプルで動作確認してください。
      </p>

      <div className="select-row">
        <label htmlFor="swell-files">HTML フォルダをアップロード</label>
        <input
          id="swell-files"
          ref={fileRef}
          type="file"
          multiple
          {...({ webkitdirectory: '', directory: '' } as React.InputHTMLAttributes<HTMLInputElement>)}
          disabled={running}
          onChange={(e) => setFiles(e.target.files)}
        />
        <p className="page-lead" style={{ margin: '0.35rem 0 0', fontSize: '0.82rem' }}>
          選択中: {fileSummary()} · CSS/JS も同フォルダにあれば一緒に送れます
        </p>
      </div>

      <div className="select-row">
        <label htmlFor="swell-select">選択パターン（カンマ区切り / ワイルドカード可）</label>
        <input
          id="swell-select"
          value={select}
          onChange={(e) => setSelect(e.target.value)}
          placeholder="**/*.html / *.html / pages/*.html"
          disabled={running}
        />
        <p className="page-lead" style={{ margin: '0.35rem 0 0', fontSize: '0.82rem' }}>
          例: <code>*.html</code>（直下）· <code>**/*.html</code> / <code>all</code>（再帰）·{' '}
          <code>pages/*.html</code>
        </p>
      </div>

      <div className="select-controls">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void runUpload()}
          disabled={running || !files?.length}
        >
          {running ? '実行中…' : 'アップロードして実行'}
        </button>
        <button type="button" className="btn" onClick={() => void runSample()} disabled={running}>
          サンプル実行
        </button>
      </div>

      <p className="page-lead" style={{ margin: 0 }}>
        解析 → SWELL 変換 → validate → deploy → visual → レポート。Git push は CLI で実行してください。
        ローカル CLI: <code>python wpaipublish.py swell pipeline demo --source-dir C:\test --select &quot;*.html&quot;</code>
      </p>

      {error && (
        <pre className="select-msg err" style={{ whiteSpace: 'pre-wrap' }}>
          {error}
        </pre>
      )}

      {result && (
        <div className="select-result">
          <p>
            セッション: <code>{result.session_id || '-'}</code> · {result.ok ? 'OK' : 'NG'}
          </p>
          {result.source_dir && (
            <p>
              source: <code>{result.source_dir}</code>
            </p>
          )}
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
