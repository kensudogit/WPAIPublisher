import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import { existsSync } from 'fs'
import { readdir, readFile, stat } from 'fs/promises'
import { join } from 'path'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

function repoRoot(): string {
  const envRoot = process.env.WPAI_ROOT
  const candidates = [
    envRoot,
    join(process.cwd(), '..'),
    process.cwd(),
    '/workspace',
    '/app',
  ].filter(Boolean) as string[]
  for (const dir of candidates) {
    if (existsSync(join(dir, 'wpaipublish.py')) || existsSync(join(dir, 'scripts', 'test', 'run_tests.py'))) {
      return dir
    }
  }
  return envRoot || join(process.cwd(), '..')
}

function resultsCandidates(): string[] {
  const root = repoRoot()
  return [
    join(root, 'output', 'test-results'),
    '/output/test-results',
    join(process.cwd(), 'output', 'test-results'),
  ]
}

function resultsDir(): string {
  for (const dir of resultsCandidates()) {
    if (existsSync(dir)) return dir
  }
  return resultsCandidates()[0]
}

/** ユーザーが「pytest -k Foo」と貼っても Foo だけにする */
export function normalizeKeyword(raw?: string | null): string | undefined {
  if (!raw) return undefined
  let k = raw.trim()
  if (!k) return undefined
  k = k.replace(/^pytest\s+/i, '')
  k = k.replace(/^-k\s+/i, '')
  k = k.replace(/^--keyword\s+/i, '')
  k = k.replace(/^["']|["']$/g, '')
  return k.trim() || undefined
}

function runPython(args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const py = process.env.PYTHON_BIN || 'python3'
    const child = spawn(py, args, {
      cwd: repoRoot(),
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1',
      },
    })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (d) => {
      stdout += d.toString()
    })
    child.stderr.on('data', (d) => {
      stderr += d.toString()
    })
    child.on('close', (code) => {
      resolve({ code: code ?? 1, stdout, stderr })
    })
    child.on('error', (err) => {
      resolve({
        code: 1,
        stdout,
        stderr: `${err}\nPython が見つかりません。ローカルでは python wpaipublish.py test run を実行してください。`,
      })
    })
  })
}

async function readLatest(): Promise<object | null> {
  for (const dir of resultsCandidates()) {
    try {
      return JSON.parse(await readFile(join(dir, 'latest.json'), 'utf-8'))
    } catch {
      // try next
    }
  }
  return null
}

async function listRuns(limit = 20) {
  const seen = new Set<string>()
  const rows: Array<{
    id: string
    status?: string
    summary?: object
    started_at?: string
    finished_at?: string
    duration_sec?: number
    mtime: number
  }> = []

  for (const dir of resultsCandidates()) {
    try {
      const st = await stat(dir)
      if (!st.isDirectory()) continue
    } catch {
      continue
    }
    const names = await readdir(dir)
    for (const name of names) {
      if (!name.endsWith('.json') || name === 'latest.json') continue
      const path = join(dir, name)
      try {
        const raw = await readFile(path, 'utf-8')
        const data = JSON.parse(raw) as {
          id?: string
          status?: string
          summary?: object
          started_at?: string
          finished_at?: string
          duration_sec?: number
        }
        const id = data.id || name.replace(/\.json$/, '')
        if (seen.has(id)) continue
        seen.add(id)
        const st = await stat(path)
        rows.push({
          id,
          status: data.status,
          summary: data.summary,
          started_at: data.started_at,
          finished_at: data.finished_at,
          duration_sec: data.duration_sec,
          mtime: st.mtimeMs,
        })
      } catch {
        // skip
      }
    }
  }
  rows.sort((a, b) => b.mtime - a.mtime)
  return rows.slice(0, limit).map(({ mtime: _m, ...rest }) => rest)
}

async function readRun(id: string) {
  for (const dir of resultsCandidates()) {
    const path = join(dir, id === 'latest' ? 'latest.json' : `${id}.json`)
    try {
      return JSON.parse(await readFile(path, 'utf-8'))
    } catch {
      // try next
    }
  }
  return null
}

export async function GET(req: NextRequest) {
  const id = req.nextUrl.searchParams.get('id')
  if (id) {
    const report = await readRun(id)
    if (!report) {
      return NextResponse.json({ error: `run not found: ${id}` }, { status: 404 })
    }
    return NextResponse.json(report)
  }

  const runs = await listRuns()
  const latest = await readLatest()
  return NextResponse.json({
    runs,
    latest,
    meta: {
      repo_root: repoRoot(),
      results_dir: resultsDir(),
      has_python_runner: existsSync(join(repoRoot(), 'scripts', 'test', 'run_tests.py')),
    },
  })
}

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as {
    path?: string
    keyword?: string
  }
  const keyword = normalizeKeyword(body.keyword)
  const script = join(repoRoot(), 'scripts', 'test', 'run_tests.py')

  if (!existsSync(script)) {
    // ビルド時結果があればそれを返す（実行不可環境向け）
    const latest = await readLatest()
    if (latest) {
      return NextResponse.json({
        ...latest,
        note: 'この環境では pytest を再実行できません。ビルド時の結果を表示しています。ローカルでは: python wpaipublish.py test run',
        keyword_applied: keyword ?? null,
      })
    }
    return NextResponse.json(
      {
        error:
          'テスト実行環境がありません（scripts/test/run_tests.py 未配置）。Railway を再デプロイするか、ローカルで python wpaipublish.py test run を実行してください。',
        code: 1,
      },
      { status: 503 },
    )
  }

  const args = [script, 'run', '--json']
  if (body.path) args.push('--path', body.path)
  if (keyword) args.push('-k', keyword)

  const result = await runPython(args)
  let report: Record<string, unknown> | null = null
  try {
    const lines = result.stdout.trim().split('\n').filter(Boolean)
    report = JSON.parse(lines[lines.length - 1] || '{}') as Record<string, unknown>
  } catch {
    report = null
  }

  if (!report) {
    return NextResponse.json(
      {
        error:
          result.stderr?.trim() ||
          result.stdout?.trim() ||
          'test run failed（Python / pytest を確認してください）',
        code: result.code,
        keyword_applied: keyword ?? null,
      },
      { status: 500 },
    )
  }

  report.keyword_applied = keyword ?? null
  return NextResponse.json(report)
}
