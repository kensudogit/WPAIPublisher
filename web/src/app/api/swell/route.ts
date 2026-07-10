import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import { existsSync } from 'fs'
import { readFile } from 'fs/promises'
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

export async function GET(req: NextRequest) {
  const session = req.nextUrl.searchParams.get('session')
  if (!session) {
    return NextResponse.json({ error: 'session required' }, { status: 400 })
  }
  const base = join(repoRoot(), 'output', session)
  const mdPath = join(base, 'change_report.md')
  const jsonPath = join(base, 'change_report.json')
  const structurePath = join(base, 'structure.json')
  const visualPath = join(base, 'visual_regression.json')

  const readJson = async (p: string) => {
    try {
      return JSON.parse(await readFile(p, 'utf-8'))
    } catch {
      return null
    }
  }
  const readText = async (p: string) => {
    try {
      return await readFile(p, 'utf-8')
    } catch {
      return null
    }
  }

  return NextResponse.json({
    session,
    report: await readJson(jsonPath),
    markdown: await readText(mdPath),
    structure: await readJson(structurePath),
    visual: await readJson(visualPath),
  })
}

export async function POST(req: NextRequest) {
  const body = (await req.json()) as {
    source_dir?: string
    select?: string[]
    session_id?: string
    theme_slug?: string
    skip_git?: boolean
    skip_deploy?: boolean
    skip_visual?: boolean
    visual_update?: boolean
  }

  const script = join(repoRoot(), 'scripts', 'swell', 'run_pipeline.py')
  const args = [script, '--json', '--theme-slug', body.theme_slug || 'swell-child']
  if (body.session_id) args.push(body.session_id)
  if (body.source_dir) {
    args.push('--source-dir', body.source_dir)
    for (const sel of body.select || []) {
      args.push('--select', sel)
    }
  }
  if (body.skip_git !== false) args.push('--skip-git') // Web 既定は push しない
  if (body.skip_deploy) args.push('--skip-deploy')
  if (body.skip_visual) args.push('--skip-visual')
  if (body.visual_update) args.push('--visual-update')

  const result = await runPython(args)
  let data: object | null = null
  try {
    const lines = result.stdout.trim().split('\n').filter(Boolean)
    data = JSON.parse(lines[lines.length - 1] || '{}')
  } catch {
    data = null
  }
  if (!data) {
    return NextResponse.json(
      { error: result.stderr || result.stdout || 'pipeline failed', code: result.code },
      { status: 500 },
    )
  }
  return NextResponse.json(data)
}
