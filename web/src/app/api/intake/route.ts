import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import { join } from 'path'
import { existsSync } from 'fs'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

function repoRoot(): string {
  const candidates = [
    join(process.cwd(), '..'),
    process.cwd(),
    '/app',
  ]
  for (const dir of candidates) {
    if (existsSync(join(dir, 'wpaipublish.py'))) return dir
  }
  return join(process.cwd(), '..')
}

function runPython(args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const root = repoRoot()
    const py = process.env.PYTHON_BIN || 'python'
    const child = spawn(py, args, { cwd: root, env: process.env })
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

export async function GET(req: NextRequest) {
  const dir = req.nextUrl.searchParams.get('dir')
  if (!dir) {
    return NextResponse.json({ error: 'dir query required' }, { status: 400 })
  }

  const script = join(repoRoot(), 'scripts', 'intake', 'select_files.py')
  const result = await runPython([script, 'list', dir, '--json'])
  if (result.code !== 0) {
    return NextResponse.json(
      { error: result.stderr || result.stdout || 'list failed' },
      { status: 400 },
    )
  }
  try {
    return NextResponse.json(JSON.parse(result.stdout))
  } catch {
    return NextResponse.json({ error: 'invalid json from list', raw: result.stdout }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  const body = (await req.json()) as {
    source_dir?: string
    select?: string[]
    target_type?: string
    theme_slug?: string
    tool?: string
    notes?: string
    package_name?: string
    session_id?: string
    agent?: boolean
  }

  if (!body.source_dir || !body.select?.length) {
    return NextResponse.json({ error: 'source_dir and select[] required' }, { status: 400 })
  }

  const script = join(repoRoot(), 'scripts', 'intake', 'start_pipeline.py')
  const args = [
    script,
    body.source_dir,
    '--target-type',
    body.target_type || 'page',
    '--theme-slug',
    body.theme_slug || 'custom-theme',
    '--tool',
    body.tool || 'other',
    '--json',
  ]
  for (const sel of body.select) {
    args.push('--select', sel)
  }
  if (body.package_name) args.push('--package-name', body.package_name)
  if (body.session_id) args.push('--session-id', body.session_id)
  if (body.notes) args.push('--notes', body.notes)
  if (body.agent) args.push('--agent')

  const result = await runPython(args)
  if (result.code !== 0) {
    return NextResponse.json(
      { error: result.stderr || result.stdout || 'pipeline failed', code: result.code },
      { status: 500 },
    )
  }

  try {
    const data = JSON.parse(result.stdout.trim().split('\n').filter(Boolean).at(-1) || '{}')
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ ok: true, raw: result.stdout })
  }
}
