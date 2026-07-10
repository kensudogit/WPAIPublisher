'use client'

import { useEffect, useRef, useState } from 'react'

type PipelineResult = {
  session_id?: string
  ok?: boolean
  steps?: { step: string; ok: boolean; detail?: string }[]
  report?: string
  error?: string
  warning?: string
  validation_errors?: string[]
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
  visual?: {
    passed?: boolean
    results?: { viewport: string; passed: boolean; diffPercent?: number }[]
  } | null
  validation?: {
    valid?: boolean
    errors?: string[]
    warnings?: string[]
  } | null
}

function isHtmlName(name: string): boolean {
  const n = name.toLowerCase()
  return n.endsWith('.html') || n.endsWith('.htm')
}

function relativeUploadPath(file: File): string {
  const relRaw = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name
  const parts = relRaw.replace(/\\/g, '/').split('/').filter(Boolean)
  if (parts.length <= 1) return parts[0] || file.name
  return parts.slice(1).join('/')
}

export function SwellPipelinePanel() {
  const folderRef = useRef<HTMLInputElement>(null)
  const filesRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [htmlCount, setHtmlCount] = useState(0)
  const [select, setSelect] = useState('**/*.html')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PipelineResult | null>(null)
  const [report, setReport] = useState<ReportPayload | null>(null)

  useEffect(() => {
    const el = folderRef.current
    if (!el) return
    el.setAttribute('webkitdirectory', '')
    el.setAttribute('directory', '')
    el.setAttribute('multiple', '')
  }, [])

  function applyFiles(list: File[]) {
    setFiles(list)
    const count = list.filter((f) => isHtmlName(f.name)).length
    setHtmlCount(count)
    setError('')
    setResult(null)
    setReport(null)
    if (!count) {
      setError(
        `HTML が見つかりません（${list.length} ファイル読み込み）。.html / .htm を含むフォルダかファイルを選んでください。`,
      )
    }
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
      else if (data.warning) setError(String(data.warning))
      else if (Array.isArray(data.validation_errors) && data.validation_errors.length) {
        setError('検証警告: ' + data.validation_errors.join('; '))
      }
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
    if (!files.length) {
      setError('フォルダまたは HTML を選択してください。Railway では C:\\... パスは使えません。')
      return
    }
    if (!htmlCount) {
      setError('HTML ファイルが含まれていません')
      return
    }
    const form = new FormData()
    for (const f of files) {
      const rel = relativeUploadPath(f)
      form.append('files', f, rel)
      form.append('paths', rel)
    }
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
      else if (data.warning) setError(String(data.warning))
      else if (Array.isArray(data.validation_errors) && data.validation_errors.length) {
        setError('検証警告: ' + data.validation_errors.join('; '))
      }
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
        Railway では PC の <code>C:\test</code> は使えません。フォルダ／HTML を選ぶか、サンプル実行してください。
      </p>

      <div className="select-row">
        <label>ファイル選択</label>
        <div className="select-controls" style={{ flexWrap: 'wrap' }}>
          <button type="button" className="btn" disabled={running} onClick={() => folderRef.current?.click()}>
            フォルダを選択
          </button>
          <button type="button" className="btn" disabled={running} onClick={() => filesRef.current?.click()}>
            HTMLファイルを選択
          </button>
        </div>
        <input
          ref={folderRef}
          type="file"
          multiple
          style={{ display: 'none' }}
          onChange={(e) => applyFiles(e.target.files ? Array.from(e.target.files) : [])}
        />
        <input
          ref={filesRef}
          type="file"
          multiple
          accept=".html,.htm,text/html"
          style={{ display: 'none' }}
          onChange={(e) => applyFiles(e.target.files ? Array.from(e.target.files) : [])}
        />
        <p className="page-lead" style={{ margin: '0.35rem 0 0', fontSize: '0.82rem' }}>
          読み込み: {files.length} ファイル（HTML {htmlCount}）
        </p>
      </div>

      <div className="select-row">
        <label htmlFor="swell-select">選択パターン（ワイルドカード可）</label>
        <input
          id="swell-select"
          value={select}
          onChange={(e) => setSelect(e.target.value)}
          placeholder="**/*.html / *.html / pages/*.html"
          disabled={running}
        />
      </div>

      <div className="select-controls">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void runUpload()}
          disabled={running || !htmlCount}
        >
          {running ? '実行中…' : 'アップロードして実行'}
        </button>
        <button type="button" className="btn" onClick={() => void runSample()} disabled={running}>
          サンプル実行
        </button>
      </div>

      {error && (
        <pre
          className={result?.ok ? 'select-msg' : 'select-msg err'}
          style={{ whiteSpace: 'pre-wrap', color: result?.ok ? '#8a6d00' : undefined }}
        >
          {error}
        </pre>
      )}

      {result && (
        <div className="select-result">
          <p>
            セッション: <code>{result.session_id || '-'}</code> · {result.ok ? 'OK' : 'NG'}
          </p>
          <ul>
            {(result.steps || []).map((s) => (
              <li key={s.step}>
                [{s.ok ? 'OK' : 'NG'}] {s.step}
                {s.detail ? <small style={{ display: 'block', opacity: 0.8 }}>{s.detail}</small> : null}
              </li>
            ))}
          </ul>
          {report?.validation && (
            <p style={{ fontSize: '0.85rem' }}>
              検証: {report.validation.valid ? 'OK' : 'NG'}
              {(report.validation.warnings || []).length
                ? ` · 警告: ${(report.validation.warnings || []).join('; ')}`
                : ''}
              {(report.validation.errors || []).length
                ? ` · エラー: ${(report.validation.errors || []).join('; ')}`
                : ''}
            </p>
          )}
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
            </div>
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
