'use client'

import { useCallback, useEffect, useState } from 'react'

type Summary = {
  passed: number
  failed: number
  skipped: number
  errors: number
  total: number
}

type TestCase = {
  nodeid: string
  classname: string
  name: string
  outcome: string
  duration: number
  message?: string
}

type Report = {
  id: string
  status: string
  summary: Summary
  tests: TestCase[]
  started_at?: string
  finished_at?: string
  duration_sec?: number
  error?: string
  note?: string
  keyword_applied?: string | null
  stdout_tail?: string
  stderr_tail?: string
}

type RunRow = {
  id: string
  status?: string
  summary?: Summary
  started_at?: string
  duration_sec?: number
}

const FILTER_PRESETS = [
  { label: 'すべて', value: '' },
  { label: 'TestSlugify', value: 'TestSlugify' },
  { label: 'select', value: 'select' },
  { label: 'SWELL', value: 'swell' },
  { label: 'Validate', value: 'TestValidateManifest' },
  { label: 'Report', value: 'TestGenerateReport' },
] as const

function outcomeClass(outcome: string) {
  if (outcome === 'passed') return 'badge badge-ok'
  if (outcome === 'failed' || outcome === 'error') return 'badge badge-warn'
  return 'badge badge-muted'
}

/** 「pytest -k Foo」や「-k Foo」を貼っても Foo にする */
function normalizeKeyword(raw: string): string {
  let k = raw.trim()
  if (!k) return ''
  k = k.replace(/^pytest\s+/i, '')
  k = k.replace(/^-k\s+/i, '')
  k = k.replace(/^--keyword\s+/i, '')
  k = k.replace(/^["']|["']$/g, '')
  return k.trim()
}

export function TestResultsPanel() {
  const [runs, setRuns] = useState<RunRow[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [keyword, setKeyword] = useState('')

  const refresh = useCallback(async (id?: string) => {
    setLoading(true)
    setError('')
    try {
      const listRes = await fetch('/api/tests')
      if (!listRes.ok) throw new Error(`HTTP ${listRes.status}`)
      const listData = (await listRes.json()) as { runs: RunRow[]; latest: Report | null }
      setRuns(listData.runs || [])

      const target = id || listData.latest?.id
      if (target) {
        const detailRes = await fetch(`/api/tests?id=${encodeURIComponent(target)}`)
        if (detailRes.ok) {
          setReport((await detailRes.json()) as Report)
        } else if (listData.latest) {
          setReport(listData.latest)
        }
      } else {
        setReport(listData.latest)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  async function runTests() {
    setRunning(true)
    setError('')
    const normalized = normalizeKeyword(keyword)
    if (normalized !== keyword.trim()) {
      setKeyword(normalized)
    }
    try {
      const res = await fetch('/api/tests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: normalized || undefined }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || `HTTP ${res.status}`)
      }
      setReport(data as Report)
      if ((data as Report).id) {
        await refresh((data as Report).id)
      } else {
        await refresh()
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
    }
  }

  const summary = report?.summary

  return (
    <div className="test-panel">
      <div className="select-row">
        <label htmlFor="test-filter">フィルタ（任意・クラス名やキーワードのみ）</label>
        <p className="page-lead" style={{ margin: '0 0 0.5rem', fontSize: '0.85rem' }}>
          <code>pytest -k</code> は不要です。空欄＝全テスト。例: <code>TestSlugify</code> · <code>select</code> ·{' '}
          <code>swell</code>
        </p>
        <div className="select-controls">
          <input
            id="test-filter"
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="空欄で全件 / 例: TestSlugify"
            disabled={running}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void runTests()
            }}
          />
          <button type="button" className="btn btn-primary" onClick={() => void runTests()} disabled={running}>
            {running ? '実行中…' : 'テスト実行'}
          </button>
          <button type="button" className="btn" onClick={() => void refresh()} disabled={running || loading}>
            再読込
          </button>
        </div>
        <div className="select-toolbar" style={{ marginTop: '0.5rem' }}>
          {FILTER_PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              className="btn-ghost"
              disabled={running}
              onClick={() => setKeyword(p.value)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="select-msg err">{error}</p>}
      {report?.note && <p className="select-msg ok">{report.note}</p>}

      {summary && (
        <div className="test-summary" aria-live="polite">
          <span className={report?.status === 'passed' ? 'badge badge-ok' : 'badge badge-warn'}>
            {report?.status}
          </span>
          <span>Pass {summary.passed}</span>
          <span>Fail {summary.failed}</span>
          <span>Skip {summary.skipped}</span>
          <span>Error {summary.errors}</span>
          <span>{report?.duration_sec ?? 0}s</span>
          <span className="test-run-id">
            <code>{report?.id}</code>
          </span>
          {report?.keyword_applied ? (
            <span>
              filter: <code>{report.keyword_applied}</code>
            </span>
          ) : null}
        </div>
      )}

      {report?.error && <p className="select-msg err">{report.error}</p>}

      <div className="test-layout">
        <div className="panel test-runs">
          <div className="panel-head">
            <h2>実行履歴</h2>
          </div>
          <div className="panel-body">
            {loading && !runs.length ? (
              <p className="empty">読み込み中…</p>
            ) : !runs.length ? (
              <p className="empty">
                まだ実行結果がありません。フィルタは空のまま「テスト実行」を押してください（
                <code>pytest -k</code> と書かないでください）。
              </p>
            ) : (
              <ul className="file-list">
                {runs.map((r) => (
                  <li key={r.id}>
                    <button
                      type="button"
                      className={`test-run-btn${report?.id === r.id ? ' is-active' : ''}`}
                      onClick={() => void refresh(r.id)}
                    >
                      <strong>{r.id}</strong>
                      <small>
                        {r.status} · P{r.summary?.passed ?? 0}/F{r.summary?.failed ?? 0} ·{' '}
                        {r.duration_sec ?? 0}s
                      </small>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="panel test-detail">
          <div className="panel-head">
            <h2>ケース詳細</h2>
          </div>
          <div className="panel-body">
            {!report ? (
              <p className="empty">レポートを選択するか、テストを実行してください。</p>
            ) : !report.tests?.length ? (
              <p className="empty">ケースがありません。</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>結果</th>
                    <th>クラス / ケース</th>
                    <th>時間</th>
                  </tr>
                </thead>
                <tbody>
                  {report.tests.map((t) => (
                    <tr key={t.nodeid}>
                      <td>
                        <span className={outcomeClass(t.outcome)}>{t.outcome}</span>
                      </td>
                      <td>
                        <div className="test-case-name">
                          <strong>{t.name}</strong>
                          <small>{t.classname || t.nodeid}</small>
                          {t.message ? <pre className="test-msg">{t.message}</pre> : null}
                        </div>
                      </td>
                      <td>{t.duration}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
