'use client'

import { useRef, useState } from 'react'

type HtmlFile = {
  path: string
  name: string
  size: number
  companions: string[]
}

function isHtmlName(name: string): boolean {
  const n = name.toLowerCase()
  return n.endsWith('.html') || n.endsWith('.htm')
}

/** webkitRelativePath からアップロードルート相対パスを作る */
function relativeUploadPath(file: File): string {
  const relRaw = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name
  const parts = relRaw.replace(/\\/g, '/').split('/').filter(Boolean)
  // folder/a.html → a.html / folder/pages/a.html → pages/a.html
  // 単一ファイル選択時は name のみ
  if (parts.length <= 1) return parts[0] || file.name
  return parts.slice(1).join('/')
}

function buildHtmlList(all: File[]): { htmls: HtmlFile[]; otherExts: string[] } {
  const rels = all.map((f) => ({ file: f, path: relativeUploadPath(f) }))
  const otherExts = [
    ...new Set(
      all
        .filter((f) => !isHtmlName(f.name))
        .map((f) => {
          const i = f.name.lastIndexOf('.')
          return i >= 0 ? f.name.slice(i).toLowerCase() : '(拡張子なし)'
        }),
    ),
  ]
  const htmls: HtmlFile[] = []
  for (const { file, path } of rels) {
    if (!isHtmlName(file.name)) continue
    const stem = path.replace(/\.html?$/i, '')
    const baseName = path.split('/').pop() || path
    const companions = rels
      .map((r) => r.path)
      .filter((p) => {
        if (p === path) return false
        const pStem = p.replace(/\.[^.]+$/, '')
        return pStem === stem || p.startsWith(stem + '.')
      })
    htmls.push({ path, name: baseName, size: file.size, companions })
  }
  // パスでソート・重複排除
  const seen = new Set<string>()
  const unique = htmls.filter((h) => {
    if (seen.has(h.path)) return false
    seen.add(h.path)
    return true
  })
  unique.sort((a, b) => a.path.localeCompare(b.path))
  return { htmls: unique, otherExts }
}

export function HtmlSelectPanel() {
  const folderRef = useRef<HTMLInputElement>(null)
  const filesRef = useRef<HTMLInputElement>(null)
  const [uploadFiles, setUploadFiles] = useState<File[]>([])
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
  const [mode, setMode] = useState<'upload' | 'sample'>('upload')

  function applyFileList(list: File[], label: string) {
    setUploadFiles(list)
    setMode('upload')
    setResult(null)
    setError(null)
    const { htmls, otherExts } = buildHtmlList(list)
    setFiles(htmls)
    setSelected(new Set(htmls.map((h) => h.path)))
    if (!htmls.length) {
      setMessage(null)
      setError(
        `HTML が見つかりませんでした（読み込み ${list.length} ファイル）。` +
          (otherExts.length
            ? ` 検出した拡張子: ${otherExts.join(', ')}。.html / .htm を含むフォルダを選んでください。`
            : ' 空のフォルダか、ファイルが選択されていません。「HTMLファイルを選択」も試してください。'),
      )
      return
    }
    setMessage(`${label}: ${htmls.length} 件の HTML を表示しています`)
  }

  function onFolderChange(e: React.ChangeEvent<HTMLInputElement>) {
    const list = e.target.files ? Array.from(e.target.files) : []
    e.target.value = ''
    if (!list.length) {
      setError('ファイルが選択されていません')
      return
    }
    applyFileList(list, 'フォルダ内ファイル')
  }

  function onFilesChange(e: React.ChangeEvent<HTMLInputElement>) {
    const list = e.target.files ? Array.from(e.target.files) : []
    e.target.value = ''
    if (!list.length) {
      setError('ファイルが選択されていません')
      return
    }
    applyFileList(list, 'ファイル')
  }

  async function listSample() {
    setLoading(true)
    setError(null)
    setMessage(null)
    setResult(null)
    setUploadFiles([])
    setMode('sample')
    try {
      const res = await fetch('/api/intake?sample=1')
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || '一覧取得に失敗しました')
      const listed = (data.files || []) as HtmlFile[]
      setFiles(listed)
      setSelected(new Set(listed.map((f) => f.path)))
      setMessage(`サンプル: ${listed.length} 件の HTML（${data.source_dir || 'intake/samples/multi-html'}）`)
      if (!listed.length) {
        setError('サンプル HTML がサーバーにありません。再デプロイが必要です。')
      }
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
      if (mode === 'upload' && uploadFiles.length) {
        const form = new FormData()
        for (const f of uploadFiles) {
          // 相対パスを filename として渡す（サーバー側で webkitRelativePath が落ちる場合の保険）
          const rel = relativeUploadPath(f)
          form.append('files', f, rel)
          form.append('paths', rel)
        }
        form.set('select', Array.from(selected).join(','))
        form.set('target_type', targetType)
        res = await fetch('/api/intake', { method: 'POST', body: form })
      } else {
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
      if (!data.session_id) {
        throw new Error(data.error || data.raw || 'session_id が返りませんでした')
      }
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
        Railway では <code>C:\test</code> のようなパス指定はできません。下のボタンでフォルダまたは HTML
        ファイルを選ぶと、すぐ一覧が表示されます。
      </p>

      <div className="select-row">
        <label>ファイル選択</label>
        <div className="select-controls" style={{ flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn"
            disabled={loading}
            onClick={() => folderRef.current?.click()}
          >
            フォルダ内のファイルを選択
          </button>
          <button
            type="button"
            className="btn"
            disabled={loading}
            onClick={() => filesRef.current?.click()}
          >
            HTMLファイルを選択
          </button>
          <button type="button" className="btn" onClick={() => void listSample()} disabled={loading}>
            サンプル一覧
          </button>
        </div>
        {/* webkitdirectory は使わない（ダイアログにフォルダしか出ない） */}
        <input
          ref={folderRef}
          type="file"
          multiple
          accept=".html,.htm,.css,.js,.mjs,.json,text/html,text/css,text/javascript,application/json"
          style={{ display: 'none' }}
          onChange={onFolderChange}
        />
        <input
          ref={filesRef}
          type="file"
          multiple
          accept=".html,.htm,text/html"
          style={{ display: 'none' }}
          onChange={onFilesChange}
        />
        <p className="page-lead" style={{ margin: '0.35rem 0 0', fontSize: '0.82rem' }}>
          フォルダへ移動してファイルを表示・選択（Ctrl+A でまとめて可）。読み込み: {uploadFiles.length}{' '}
          ファイル · 表示中 HTML: {files.length} 件
        </p>
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
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setSelected(new Set())}
              disabled={loading}
            >
              クリア
            </button>
          </div>
          <ul className="file-list" role="listbox" aria-label="HTML ファイル">
            {files.map((f) => {
              const checked = selected.has(f.path)
              const comps =
                f.companions.map((c) => c.split(/[/\\]/).pop()).join(', ') || 'なし'
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
