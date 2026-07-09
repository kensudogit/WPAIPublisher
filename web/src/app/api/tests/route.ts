import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import { existsSync } from 'fs'
import { readdir, readFile, stat } from 'fs/promises'
import { join } from 'path'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

function repoRoot(): string {
  const candidates = [join(process.cwd(), '..'), process.cwd(), '/app']
  for (const dir of candidates) {
    if (existsSync(join(dir, 'wpaipublish.py'))) return dir
  }
  return join(process.cwd(), '..')
}

function resultsDir(): string {
  return join(repoRoot(), 'output', 'test-results')
}

function runPython(args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const py = process.env.PYTHON_BIN || 'python'
    const child = spawn(py, args, { cwd: repoRoot(), env: process.env })
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
      resolve({ code: 1, stdout, stderr: String(err) })
    })
  })
}

async function readLatest(): Promise<object | null> {
  const path = join(resultsDir(), 'latest.json')
  try {
    return JSON.parse(await readFile(path, 'utf-8'))
  } catch {
    return null
  }
}

async function listRuns(limit = 20) {
  const dir = resultsDir()
  try {
    const st = await stat(dir)
    if (!st.isDirectory()) return []
  } catch {
    return []
  }
  const names = await readdir(dir)
  const rows: Array<{
    id: string
    status?: string
    summary?: object
    started_at?: string
    finished_at?: string
    duration_sec?: number
    mtime: number
  }> = []

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
      const st = await stat(path)
      rows.push({
        id: data.id || name.replace(/\.json$/, ''),
        status: data.status,
        summary: data.summary,
        started_at: data.started_at,
        finished_at: data.finished_at,
        duration_sec: data.duration_sec,
        mtime: st.mtimeMs,
      })
    } catch {
      // skip broken
    }
  }
  rows.sort((a, b) => b.mtime - a.mtime)
  return rows.slice(0, limit).map(({ mtime: _m, ...rest }) => rest)
}

async function readRun(id: string) {
  const path = join(resultsDir(), id === 'latest' ? 'latest.json' : `${id}.json`)
  try {
    return JSON.parse(await readFile(path, 'utf-8'))
  } catch {
    return null
  }
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
  return NextResponse.json({ runs, latest })
}

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => ({}))) as {
    path?: string
    keyword?: string
  }
  const script = join(repoRoot(), 'scripts', 'test', 'run_tests.py')
  const args = [script, 'run', '--json']
  if (body.path) args.push('--path', body.path)
  if (body.keyword) args.push('-k', body.keyword)

  const result = await runPython(args)
  let report: object | null = null
  try {
    const lines = result.stdout.trim().split('\n').filter(Boolean)
    report = JSON.parse(lines[lines.length - 1] || '{}')
  } catch {
    report = null
  }

  if (!report) {
    return NextResponse.json(
      {
        error: result.stderr || result.stdout || 'test run failed',
        code: result.code,
      },
      { status: 500 },
    )
  }

  return NextResponse.json(report, { status: result.code === 0 ? 200 : 200 })
}
