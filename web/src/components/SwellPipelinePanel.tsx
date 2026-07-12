'use client'

import { useRef, useState, type ChangeEvent } from 'react'

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
  session?: string
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
  regenerated?: boolean
  loaded_at?: string
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

/** Railway Web UI の実用上限（タイムアウト・ボディサイズ対策） */
const MAX_UPLOAD_FILES = 40
const MAX_UPLOAD_HTML = 30

async function readApiJson(res: Response): Promise<Record<string, unknown>> {
  const text = await res.text()
  if (!text) {
    throw new Error(
      res.ok
        ? 'サーバーから空の応答が返りました'
        : `リクエスト失敗 (${res.status})。ファイル数・サイズを減らして再試行してください。`,
    )
  }
  try {
    return JSON.parse(text) as Record<string, unknown>
  } catch {
    const snippet = text.replace(/\s+/g, ' ').slice(0, 180)
    throw new Error(
      `サーバーエラー (${res.status}): JSON 以外の応答です。` +
        (snippet ? ` ${snippet}` : '') +
        ' HTML を 30 件以下に絞るか「サンプル実行」を試してください。',
    )
  }
}

export function SwellPipelinePanel() {
  const folderFilesRef = useRef<HTMLInputElement>(null)
  const htmlFilesRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [htmlCount, setHtmlCount] = useState(0)
  const [select, setSelect] = useState('**/*.html')
  const [running, setRunning] = useState(false)
  const [reloading, setReloading] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [result, setResult] = useState<PipelineResult | null>(null)
  const [report, setReport] = useState<ReportPayload | null>(null)

  const fileEntries = files.map((f) => ({
    file: f,
    path: relativeUploadPath(f),
    html: isHtmlName(f.name),
  }))

  function applyFiles(list: File[]) {
    setFiles(list)
    const count = list.filter((f) => isHtmlName(f.name)).length
    setHtmlCount(count)
    setError('')
    setInfo('')
    setResult(null)
    setReport(null)
    if (!count) {
      setError(
        `HTML が見つかりません（${list.length} ファイル読み込み）。.html / .htm を含むフォルダかファイルを選んでください。`,
      )
      return
    }
    if (count > MAX_UPLOAD_HTML || list.length > MAX_UPLOAD_FILES) {
      setError(
        `読み込み過多: HTML ${count} / 合計 ${list.length} ファイル。` +
          ` Web UI では HTML ${MAX_UPLOAD_HTML}・合計 ${MAX_UPLOAD_FILES} までです。` +
          ' サブフォルダを選ぶか、少数の HTML だけ選んでください。大量はローカル CLI を使います。',
      )
    }
  }

  function onPickerChange(e: ChangeEvent<HTMLInputElement>) {
    applyFiles(e.target.files ? Array.from(e.target.files) : [])
    // 同じフォルダを再選択できるようにクリア
    e.target.value = ''
  }

  async function fetchReport(session: string, regenerate: boolean): Promise<ReportPayload> {
    const qs = new URLSearchParams({
      session,
      _: String(Date.now()),
    })
    if (regenerate) qs.set('regenerate', '1')
    const r = await fetch(`/api/swell?${qs.toString()}`, {
      method: 'GET',
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    })
    const data = await readApiJson(r)
    if (!r.ok) {
      throw new Error(String(data.error || `レポート取得に失敗しました (${r.status})`))
    }
    return data as ReportPayload
  }

  function applyPipelineResult(data: Record<string, unknown>) {
    setResult(data as PipelineResult)
    if (data.ok === false && data.error) setError(String(data.error))
    else if (data.warning) setError(String(data.warning))
    else if (Array.isArray(data.validation_errors) && data.validation_errors.length) {
      setError('検証警告: ' + data.validation_errors.join('; '))
    }
  }

  async function runWithFormData(form: FormData) {
    setInfo('アップロード中…（完了までページを閉じないでください）')
    try {
      const res = await fetch('/api/swell', { method: 'POST', body: form })
      const data = await readApiJson(res)
      if (!res.ok) throw new Error(String(data.error || 'pipeline failed'))
      setInfo('')
      applyPipelineResult(data)
      if (data.session_id) {
        try {
          setReport(await fetchReport(String(data.session_id), false))
        } catch (e) {
          setInfo(e instanceof Error ? e.message : String(e))
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setInfo('')
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
    if (htmlCount > MAX_UPLOAD_HTML || files.length > MAX_UPLOAD_FILES) {
      setError(
        `ファイルが多すぎます（HTML ${htmlCount} / 合計 ${files.length}）。` +
          ` 上限は HTML ${MAX_UPLOAD_HTML}・合計 ${MAX_UPLOAD_FILES} です。` +
          ' 少数に絞るか「サンプル実行」を使ってください。',
      )
      return
    }

    setRunning(true)
    setError('')
    setInfo('準備中…')
    setResult(null)
    setReport(null)

    // UI を先に更新してから FormData 構築（大量ファイルで固まったように見えないように）
    await new Promise((r) => setTimeout(r, 0))

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
    setInfo('サンプル実行中…')
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
      const data = await readApiJson(res)
      if (!res.ok) throw new Error(String(data.error || 'pipeline failed'))
      setInfo('')
      applyPipelineResult(data)
      if (data.session_id) {
        try {
          setReport(await fetchReport(String(data.session_id), false))
        } catch (e) {
          setInfo(e instanceof Error ? e.message : String(e))
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setInfo('')
    } finally {
      setRunning(false)
    }
  }

  async function loadReport(session: string) {
    setReloading(true)
    setError('')
    setInfo('レポートを再生成しています…')
    try {
      const data = await fetchReport(session, true)
      setReport(data)
      const when = data.loaded_at ? new Date(data.loaded_at).toLocaleString('ja-JP') : ''
      setInfo(
        data.regenerated
          ? `レポートを再生成しました${when ? `（${when}）` : ''}`
          : `レポートを読み込みました${when ? `（${when}）` : ''}`,
      )
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setInfo('')
    } finally {
      setReloading(false)
    }
  }

  const hasReportView = Boolean(report?.report || report?.markdown)

  return (
    <div className="select-panel">
      <p className="page-lead" style={{ margin: 0, fontSize: '0.9rem' }}>
        Railway では PC の <code>C:\test</code> は使えません。フォルダ／HTML を選ぶか、サンプル実行してください。
        Web では一度に HTML {MAX_UPLOAD_HTML} 件まで（大量はローカル CLI）。
      </p>

      <div className="select-row">
        <label>ファイル選択</label>
        <div className="select-controls" style={{ flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn"
            disabled={running}
            onClick={() => folderFilesRef.current?.click()}
          >
            フォルダ内のファイルを選択
          </button>
          <button
            type="button"
            className="btn"
            disabled={running}
            onClick={() => htmlFilesRef.current?.click()}
          >
            HTMLのみ選択
          </button>
        </div>
        {/* webkitdirectory は使わない（Windows ではフォルダしか出ず中身が見えない） */}
        <input
          ref={folderFilesRef}
          type="file"
          multiple
          accept=".html,.htm,.css,.js,.mjs,.json,text/html,text/css,text/javascript,application/json"
          style={{ display: 'none' }}
          onChange={onPickerChange}
        />
        <input
          ref={htmlFilesRef}
          type="file"
          multiple
          accept=".html,.htm,text/html"
          style={{ display: 'none' }}
          onChange={onPickerChange}
        />
        <p className="page-lead" style={{ margin: '0.35rem 0 0', fontSize: '0.82rem' }}>
          <code>C:\test</code> などへ移動し、ファイル一覧から選択（Ctrl+A でまとめて可）。
          読み込み: {files.length} ファイル（HTML {htmlCount}）
          {htmlCount > MAX_UPLOAD_HTML || files.length > MAX_UPLOAD_FILES
            ? ` · 上限超過（HTML ${MAX_UPLOAD_HTML} / 合計 ${MAX_UPLOAD_FILES}）`
            : ''}
        </p>
        {fileEntries.length > 0 && (
          <ul className="file-list" role="list" aria-label="選択中のファイル" style={{ marginTop: '0.5rem' }}>
            {fileEntries.slice(0, 80).map((f) => (
              <li key={f.path + f.file.size}>
                <span className="file-meta">
                  <strong>{f.path}</strong>
                  <small>
                    {(f.file.size / 1024).toFixed(1)} KB
                    {f.html ? ' · HTML' : ''}
                  </small>
                </span>
              </li>
            ))}
            {fileEntries.length > 80 ? (
              <li>
                <span className="file-meta">
                  <small>…ほか {fileEntries.length - 80} 件</small>
                </span>
              </li>
            ) : null}
          </ul>
        )}
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
          disabled={
            running ||
            !htmlCount ||
            htmlCount > MAX_UPLOAD_HTML ||
            files.length > MAX_UPLOAD_FILES
          }
          title={
            htmlCount > MAX_UPLOAD_HTML || files.length > MAX_UPLOAD_FILES
              ? `上限: HTML ${MAX_UPLOAD_HTML} / 合計 ${MAX_UPLOAD_FILES}`
              : undefined
          }
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
      {info && !error && (
        <p className="select-msg ok" style={{ margin: 0 }}>
          {info}
        </p>
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
            <button
              type="button"
              className="btn"
              disabled={running || reloading}
              onClick={() => void loadReport(result.session_id!)}
            >
              {reloading ? '再生成中…' : 'レポート再読込'}
            </button>
          )}
        </div>
      )}

      {hasReportView && (
        <div className="panel" style={{ marginTop: '0.5rem' }}>
          <div className="panel-head">
            <h2>変更レポート</h2>
          </div>
          <div className="panel-body">
            {report?.report && (
              <div className="test-summary">
                <span className={report.report.overall === 'passed' ? 'badge badge-ok' : 'badge badge-warn'}>
                  {report.report.overall || report.report.status || '-'}
                </span>
                <span>{report.report.conversion?.theme_slug}</span>
                <span>blocks: {(report.report.conversion?.blocks || []).join(', ') || '-'}</span>
              </div>
            )}
            {report?.markdown ? (
              <pre className="test-msg" style={{ maxHeight: 320, marginTop: '1rem' }}>
                {report.markdown}
              </pre>
            ) : (
              <p className="page-lead" style={{ marginTop: '1rem' }}>
                Markdown レポートがありません。再読込を試してください。
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
