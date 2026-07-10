import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import { existsSync, mkdirSync, writeFileSync, rmSync } from 'fs'
import { readFile } from 'fs/promises'
import { join, dirname } from 'path'
import { randomBytes } from 'crypto'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

function repoRoot(): string {
  const envRoot = process.env.WPAI_ROOT
  const candidates = [
    envRoot,
    '/workspace',
    join(process.cwd(), '..'),
    process.cwd(),
    '/app',
  ].filter(Boolean) as string[]
  for (const dir of candidates) {
    if (
      existsSync(join(dir, 'wpaipublish.py')) ||
      existsSync(join(dir, 'scripts', 'swell', 'run_pipeline.py'))
    ) {
      return dir
    }
  }
  return envRoot || '/workspace'
}

function runPython(args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const py = process.env.PYTHON_BIN || 'python3'
    const child = spawn(py, args, {
      cwd: repoRoot(),
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
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
        stderr: `${err}\nPython / パイプライン実行環境が見つかりません。`,
      })
    })
  })
}

function looksLikeWindowsPath(p: string): boolean {
  return /^[a-zA-Z]:[\\/]/.test(p) || p.startsWith('\\\\')
}

export async function GET(req: NextRequest) {
  const session = req.nextUrl.searchParams.get('session')
  if (!session) {
    return NextResponse.json({ error: 'session required' }, { status: 400 })
  }
  const base = join(repoRoot(), 'output', session)
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
    report: await readJson(join(base, 'change_report.json')),
    markdown: await readText(join(base, 'change_report.md')),
    structure: await readJson(join(base, 'structure.json')),
    visual: await readJson(join(base, 'visual_regression.json')),
  })
}

async function saveUploads(form: FormData): Promise<{ dir: string; files: string[] }> {
  const root = repoRoot()
  const uploadId = `upload-${Date.now()}-${randomBytes(3).toString('hex')}`
  const dir = join(root, 'intake', 'uploads', uploadId)
  mkdirSync(dir, { recursive: true })

  const files: string[] = []
  const entries = form.getAll('files')
  for (const entry of entries) {
    if (typeof entry === 'string') continue
    const file = entry as File
    const rel =
      (file as File & { webkitRelativePath?: string }).webkitRelativePath ||
      file.name
    // strip leading folder name from webkitdirectory (folder/a.html -> a.html or keep nested)
    const parts = rel.replace(/\\/g, '/').split('/').filter(Boolean)
    const relPath = parts.length > 1 ? parts.slice(1).join('/') : parts[0] || file.name
    const dest = join(dir, relPath)
    mkdirSync(dirname(dest), { recursive: true })
    const buf = Buffer.from(await file.arrayBuffer())
    writeFileSync(dest, buf)
    files.push(relPath)
  }
  return { dir, files }
}

export async function POST(req: NextRequest) {
  const contentType = req.headers.get('content-type') || ''
  let sourceDir = ''
  let select: string[] = []
  let sessionId = ''
  let themeSlug = 'swell-child'
  let skipGit = true
  let skipDeploy = false
  let skipVisual = false
  let visualUpdate = true
  let uploadDir: string | null = null

  try {
    if (contentType.includes('multipart/form-data')) {
      const form = await req.formData()
      const uploaded = await saveUploads(form)
      uploadDir = uploaded.dir
      sourceDir = uploaded.dir
      const selectRaw = String(form.get('select') || '**/*.html')
      select = selectRaw
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      if (!select.length) select = ['**/*.html']
      sessionId = String(form.get('session_id') || '')
      themeSlug = String(form.get('theme_slug') || 'swell-child')
      skipGit = String(form.get('skip_git') ?? 'true') !== 'false'
      skipDeploy = String(form.get('skip_deploy') || '') === 'true'
      skipVisual = String(form.get('skip_visual') || '') === 'true'
      visualUpdate = String(form.get('visual_update') ?? 'true') !== 'false'

      if (!uploaded.files.length) {
        return NextResponse.json(
          { error: 'アップロードされたファイルがありません。HTML（と CSS/JS）を選択してください。' },
          { status: 400 },
        )
      }
    } else {
      const body = (await req.json()) as {
        source_dir?: string
        select?: string[]
        session_id?: string
        theme_slug?: string
        skip_git?: boolean
        skip_deploy?: boolean
        skip_visual?: boolean
        visual_update?: boolean
        use_sample?: boolean
      }

      if (body.use_sample) {
        sourceDir = join(repoRoot(), 'intake', 'samples', 'multi-html')
        select = body.select?.length ? body.select : ['**/*.html']
      } else {
        sourceDir = body.source_dir || ''
        select = body.select || []
      }
      sessionId = body.session_id || ''
      themeSlug = body.theme_slug || 'swell-child'
      skipGit = body.skip_git !== false
      skipDeploy = !!body.skip_deploy
      skipVisual = !!body.skip_visual
      visualUpdate = body.visual_update !== false

      if (!sourceDir) {
        return NextResponse.json(
          {
            error:
              'HTML フォルダが未指定です。Railway 上ではローカルパス（例: C:\\test）は使えません。ファイルをアップロードするか「サンプル実行」を使ってください。',
          },
          { status: 400 },
        )
      }

      if (looksLikeWindowsPath(sourceDir) && !existsSync(sourceDir)) {
        return NextResponse.json(
          {
            error:
              `サーバーからローカルパスにアクセスできません: ${sourceDir}\n` +
              'Railway（クラウド）では PC 上の C:\\... は見えません。HTML ファイルをアップロードするか、CLI をローカルで実行してください。',
            hint: 'python wpaipublish.py swell pipeline demo --source-dir C:\\test --select "*.html"',
          },
          { status: 400 },
        )
      }

      if (!existsSync(sourceDir)) {
        return NextResponse.json(
          {
            error: `フォルダが見つかりません: ${sourceDir}`,
            hint: 'ファイルアップロード、または intake/samples/multi-html のサンプル実行を使ってください。',
          },
          { status: 400 },
        )
      }
    }

    const script = join(repoRoot(), 'scripts', 'swell', 'run_pipeline.py')
    if (!existsSync(script)) {
      return NextResponse.json(
        {
          error: `パイプラインスクリプトが見つかりません: ${script}`,
          repo_root: repoRoot(),
        },
        { status: 503 },
      )
    }

    const args = [script, '--json', '--theme-slug', themeSlug]
    if (sessionId) args.push(sessionId)
    args.push('--source-dir', sourceDir)
    for (const sel of select) {
      args.push('--select', sel)
    }
    if (skipGit) args.push('--skip-git')
    if (skipDeploy) args.push('--skip-deploy')
    if (skipVisual) args.push('--skip-visual')
    if (visualUpdate) args.push('--visual-update')

    const result = await runPython(args)
    let data: Record<string, unknown> | null = null
    try {
      const lines = result.stdout.trim().split('\n').filter(Boolean)
      data = JSON.parse(lines[lines.length - 1] || '{}') as Record<string, unknown>
    } catch {
      data = null
    }

    if (!data) {
      return NextResponse.json(
        {
          error: result.stderr || result.stdout || 'pipeline failed',
          code: result.code,
          source_dir: sourceDir,
        },
        { status: 500 },
      )
    }

    // ok:false でも JSON は返す（UI でステップ表示）
    if (data.ok === false && !data.error && result.stderr) {
      data.error = result.stderr.slice(-1500)
    }
    data.upload_dir = uploadDir
    data.source_dir = sourceDir
    return NextResponse.json(data)
  } catch (e) {
    if (uploadDir && existsSync(uploadDir)) {
      try {
        rmSync(uploadDir, { recursive: true, force: true })
      } catch {
        // ignore
      }
    }
    return NextResponse.json(
      { error: e instanceof Error ? e.message : String(e) },
      { status: 500 },
    )
  }
}
