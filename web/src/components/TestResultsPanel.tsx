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

function outcomeClass(outcome: string) {
  if (outcome === 'passed') return 'badge badge-ok'
  if (outcome === 'failed' || outcome === 'error') return 'badge badge-warn'
  return 'badge badge-muted'
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
        setReport(null)
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
    try {
      const res = await fetch('/api/tests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: keyword.trim() || undefined }),
      })
      const data = await res.json()
      if (!res.ok && data.error) throw new Error(data.error)
      setReport(data as Report)
      await refresh((data as Report).id)
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
        <label htmlFor="test-filter">フィルタ（pytest -k、任意）</label>
        <div className="select-controls">
          <input
            id="test-filter"
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="例: TestSlugify or select"
            disabled={running}
          />
          <button type="button" className="btn btn-primary" onClick={runTests} disabled={running}>
            {running ? '実行中…' : 'テスト実行'}
          </button>
          <button type="button" className="btn" onClick={() => void refresh()} disabled={running || loading}>
            再読込
          </button>
        </div>
      </div>

      {error && <p className="select-msg err">{error}</p>}

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
              <p className="empty">まだ実行結果がありません。「テスト実行」を押してください。</p>
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
