'use client'

import { useRef, useState } from 'react'

type HtmlFile = {
  path: string
  name: string
  size: number
  companions: string[]
}

export function HtmlSelectPanel() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploadFiles, setUploadFiles] = useState<FileList | null>(null)
  const [files, setFiles] = useState<HtmlFile[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [targetType, setTargetType] = useState('page')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{
    session_id?: string
    package?: string
    next?: string[]
    source_dir?: string
  } | null>(null)
  const [sourceDir, setSourceDir] = useState<string | null>(null)

  function fileSummary(): string {
    if (!uploadFiles?.length) return '未選択'
    const htmlCount = Array.from(uploadFiles).filter((f) =>
      f.name.toLowerCase().endsWith('.html'),
    ).length
    return `${uploadFiles.length} ファイル（HTML ${htmlCount}）`
  }

  async function listSample() {
    setLoading(true)
    setError(null)
    setMessage(null)
    setResult(null)
    try {
      const res = await fetch('/api/intake?sample=1')
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || '一覧取得に失敗しました')
      setFiles(data.files || [])
      setSelected(new Set((data.files || []).map((f: HtmlFile) => f.path)))
      setSourceDir(data.source_dir || null)
      setMessage(`サンプル: ${(data.files || []).length} 件の HTML`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setFiles([])
    } finally {
      setLoading(false)
    }
  }

  async function listFromUpload() {
    if (!uploadFiles?.length) {
      setError('フォルダを選択してください。Railway では C:\\... パスは使えません。')
      return
    }
    setLoading(true)
    setError(null)
    setMessage(null)
    setResult(null)
    try {
      // クライアント側で一覧を組み立て（アップロード後にサーバー list も可だが UX 優先）
      const htmls: HtmlFile[] = []
      const all = Array.from(uploadFiles)
      for (const f of all) {
        if (!f.name.toLowerCase().endsWith('.html')) continue
        const relRaw = (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name
        const parts = relRaw.replace(/\\/g, '/').split('/').filter(Boolean)
        const path = parts.length > 1 ? parts.slice(1).join('/') : parts[0] || f.name
        const stem = path.replace(/\.html$/i, '')
        const baseName = path.split('/').pop() || path
        const companions = all
          .map((c) => {
            const crel = (c as File & { webkitRelativePath?: string }).webkitRelativePath || c.name
            const cparts = crel.replace(/\\/g, '/').split('/').filter(Boolean)
            return cparts.length > 1 ? cparts.slice(1).join('/') : cparts[0] || c.name
          })
          .filter(
            (p) =>
              p !== path &&
              (p.startsWith(stem + '.') || p.includes('/' + stem + '.') || p.endsWith(baseName.replace(/\.html$/i, '.css')) || p.endsWith(baseName.replace(/\.html$/i, '.js'))),
          )
        htmls.push({ path, name: baseName, size: f.size, companions })
      }
      if (!htmls.length) throw new Error('HTML ファイルが含まれていません')
      setFiles(htmls)
      setSelected(new Set(htmls.map((h) => h.path)))
      setSourceDir(null) // upload 時は POST で送る
      setMessage(`${htmls.length} 件の HTML を検出しました（アップロード準備完了）`)
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
      let res: Response
      if (uploadFiles?.length && !sourceDir) {
        const form = new FormData()
        Array.from(uploadFiles).forEach((f) => form.append('files', f))
        form.set('select', Array.from(selected).join(','))
        form.set('target_type', targetType)
        res = await fetch('/api/intake', { method: 'POST', body: form })
      } else if (sourceDir) {
        res = await fetch('/api/intake', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_dir: sourceDir,
            select: Array.from(selected),
            target_type: targetType,
            use_sample: sourceDir.includes('multi-html'),
          }),
        })
      } else {
        // サンプル選択後
        res = await fetch('/api/intake', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            use_sample: true,
            select: Array.from(selected),
            target_type: targetType,
          }),
        })
      }
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
      <p className="page-lead" style={{ margin: 0, fontSize: '0.9rem' }}>
        Railway では PC の <code>C:\test</code> などローカルパスは使えません。フォルダをアップロードするか、サンプルを使ってください。
      </p>

      <div className="select-row">
        <label htmlFor="html-files">HTML フォルダをアップロード</label>
        <input
          id="html-files"
          ref={fileRef}
          type="file"
          multiple
          {...({ webkitdirectory: '', directory: '' } as React.InputHTMLAttributes<HTMLInputElement>)}
          disabled={loading}
          onChange={(e) => setUploadFiles(e.target.files)}
        />
        <p className="page-lead" style={{ margin: '0.35rem 0 0', fontSize: '0.82rem' }}>
          選択中: {fileSummary()}
        </p>
        <div className="select-controls" style={{ marginTop: '0.5rem' }}>
          <button type="button" className="btn" onClick={() => void listFromUpload()} disabled={loading || !uploadFiles?.length}>
            アップロードを一覧
          </button>
          <button type="button" className="btn" onClick={() => void listSample()} disabled={loading}>
            サンプル一覧
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
            <span>
              {selected.size} / {files.length} 選択
            </span>
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
                      <small>
                        {(f.size / 1024).toFixed(1)} KB · 関連: {comps}
                      </small>
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void startPipeline()}
            disabled={loading || selected.size === 0}
          >
            {loading ? '処理中…' : '選択してパイプライン開始'}
          </button>
        </>
      )}

      {message && <p className="select-msg ok">{message}</p>}
      {error && (
        <pre className="select-msg err" style={{ whiteSpace: 'pre-wrap' }}>
          {error}
        </pre>
      )}

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

      <p className="page-lead" style={{ margin: 0, fontSize: '0.82rem' }}>
        ローカル CLI: <code>python wpaipublish.py intake pipeline C:\test --select &quot;*.html&quot;</code>
      </p>
    </div>
  )
}
