import { NextRequest, NextResponse } from 'next/server'
import { existsSync, mkdirSync, writeFileSync } from 'fs'
import { join, dirname } from 'path'
import { randomBytes } from 'crypto'
import { looksLikeWindowsPath, parsePythonJson, repoRoot, runPython } from '@/lib/repoRoot'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

async function saveUploads(form: FormData): Promise<{ dir: string; files: string[] }> {
  const root = repoRoot()
  const uploadId = `upload-${Date.now()}-${randomBytes(3).toString('hex')}`
  const dir = join(root, 'intake', 'uploads', uploadId)
  mkdirSync(dir, { recursive: true })

  const pathHints = form.getAll('paths').map(String)
  const files: string[] = []
  let idx = 0
  for (const entry of form.getAll('files')) {
    if (typeof entry === 'string') continue
    const file = entry as File
    const hint = pathHints[idx] || ''
    idx += 1
    const relRaw =
      hint ||
      (file as File & { webkitRelativePath?: string }).webkitRelativePath ||
      file.name
    const parts = relRaw.replace(/\\/g, '/').split('/').filter(Boolean)
    // paths ヒントがある場合はそのまま。webkitRelativePath なら先頭フォルダを除去
    let relPath: string
    if (hint) {
      relPath = hint.replace(/\\/g, '/')
    } else if (parts.length > 1) {
      relPath = parts.slice(1).join('/')
    } else {
      relPath = parts[0] || file.name
    }
    // パストラバーサル防止
    relPath = relPath.replace(/^(\.\.\/)+/, '').replace(/^\/+/, '')
    if (!relPath || relPath.includes('..')) continue
    const dest = join(dir, relPath)
    mkdirSync(dirname(dest), { recursive: true })
    writeFileSync(dest, Buffer.from(await file.arrayBuffer()))
    files.push(relPath)
  }
  return { dir, files }
}

export async function GET(req: NextRequest) {
  const sample = req.nextUrl.searchParams.get('sample')
  const dirParam = req.nextUrl.searchParams.get('dir')

  const root = repoRoot()
  const script = join(root, 'scripts', 'intake', 'select_files.py')

  if (!existsSync(script)) {
    return NextResponse.json(
      {
        error: `select_files.py が見つかりません（repo=${root}）。Railway を再デプロイしてください。`,
        repo_root: root,
        script,
      },
      { status: 503 },
    )
  }

  let dir = dirParam || ''
  if (sample === '1' || sample === 'true') {
    dir = join(root, 'intake', 'samples', 'multi-html')
  }

  if (!dir) {
    return NextResponse.json(
      {
        error:
          'dir が未指定です。Railway では C:\\... は使えません。フォルダをアップロードするか ?sample=1 を使ってください。',
      },
      { status: 400 },
    )
  }

  if (looksLikeWindowsPath(dir) && !existsSync(dir)) {
    return NextResponse.json(
      {
        error:
          `サーバーからローカルパスにアクセスできません: ${dir}\n` +
          'Railway では PC の C:\\... は見えません。フォルダをアップロードするか「サンプル一覧」を使ってください。',
        hint: 'ローカル CLI: python wpaipublish.py intake list C:\\test',
      },
      { status: 400 },
    )
  }

  if (!existsSync(dir)) {
    return NextResponse.json({ error: `フォルダが見つかりません: ${dir}` }, { status: 400 })
  }

  const result = await runPython([script, 'list', dir, '--json'])
  if (result.code !== 0) {
    return NextResponse.json(
      { error: result.stderr || result.stdout || 'list failed', repo_root: root },
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
  const root = repoRoot()
  const script = join(root, 'scripts', 'intake', 'start_pipeline.py')
  if (!existsSync(script)) {
    return NextResponse.json(
      {
        error: `start_pipeline.py が見つかりません（repo=${root}）`,
        repo_root: root,
      },
      { status: 503 },
    )
  }

  const contentType = req.headers.get('content-type') || ''
  let sourceDir = ''
  let select: string[] = []
  let targetType = 'page'
  let themeSlug = 'custom-theme'
  let tool = 'other'
  let notes = ''
  let packageName = ''
  let sessionId = ''
  let agent = false

  if (contentType.includes('multipart/form-data')) {
    const form = await req.formData()
    const uploaded = await saveUploads(form)
    sourceDir = uploaded.dir
    const selectRaw = String(form.get('select') || '')
    if (selectRaw.trim()) {
      select = selectRaw.split(',').map((s) => s.trim()).filter(Boolean)
    } else {
      // アップロード内の html をすべて
      select = uploaded.files.filter((f) => f.toLowerCase().endsWith('.html'))
      if (!select.length) select = ['**/*.html']
    }
    targetType = String(form.get('target_type') || 'page')
    themeSlug = String(form.get('theme_slug') || 'custom-theme')
    tool = String(form.get('tool') || 'other')
    notes = String(form.get('notes') || '')
    packageName = String(form.get('package_name') || '')
    sessionId = String(form.get('session_id') || '')
    agent = String(form.get('agent') || '') === 'true'

    if (!uploaded.files.length) {
      return NextResponse.json({ error: 'アップロードファイルがありません' }, { status: 400 })
    }
  } else {
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
      use_sample?: boolean
    }

    if (body.use_sample) {
      sourceDir = join(root, 'intake', 'samples', 'multi-html')
      select = body.select?.length ? body.select : ['**/*.html']
    } else {
      sourceDir = body.source_dir || ''
      select = body.select || []
    }
    targetType = body.target_type || 'page'
    themeSlug = body.theme_slug || 'custom-theme'
    tool = body.tool || 'other'
    notes = body.notes || ''
    packageName = body.package_name || ''
    sessionId = body.session_id || ''
    agent = !!body.agent

    if (!sourceDir || !select.length) {
      return NextResponse.json(
        {
          error:
            'source_dir と select[] が必要です。Railway ではローカルパスは使えません。アップロードまたはサンプル実行を使ってください。',
        },
        { status: 400 },
      )
    }

    if (looksLikeWindowsPath(sourceDir) && !existsSync(sourceDir)) {
      return NextResponse.json(
        {
          error:
            `サーバーからローカルパスにアクセスできません: ${sourceDir}\n` +
            'フォルダをアップロードするか、ローカル CLI を使ってください。',
          hint: 'python wpaipublish.py intake pipeline C:\\test --select "*.html"',
        },
        { status: 400 },
      )
    }
  }

  const args = [
    script,
    sourceDir,
    '--target-type',
    targetType,
    '--theme-slug',
    themeSlug,
    '--tool',
    tool,
    '--json',
  ]
  for (const sel of select) {
    args.push('--select', sel)
  }
  if (packageName) args.push('--package-name', packageName)
  if (sessionId) args.push('--session-id', sessionId)
  if (notes) args.push('--notes', notes)
  if (agent) args.push('--agent')

  const result = await runPython(args)
  if (result.code !== 0) {
    return NextResponse.json(
      {
        error: result.stderr || result.stdout || 'pipeline failed',
        code: result.code,
        repo_root: root,
        source_dir: sourceDir,
      },
      { status: 500 },
    )
  }

  const data = parsePythonJson(result.stdout)
  if (!data || !data.session_id) {
    return NextResponse.json(
      {
        error:
          result.stderr?.trim() ||
          'パイプライン結果の JSON を読めませんでした（session_id なし）',
        raw: result.stdout?.slice(-2000),
        code: result.code,
        repo_root: root,
        source_dir: sourceDir,
      },
      { status: 500 },
    )
  }
  return NextResponse.json({ ...data, source_dir: sourceDir })
}
