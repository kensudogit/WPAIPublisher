import { NextRequest, NextResponse } from 'next/server'
import { existsSync, readFileSync, unlinkSync } from 'fs'
import { join } from 'path'
import { tmpdir } from 'os'
import { randomBytes } from 'crypto'
import { parsePythonJson, repoRoot, runPython } from '@/lib/repoRoot'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'
export const maxDuration = 120

const SESSION_RE = /^[a-zA-Z0-9._-]+$/

type RouteParams = { params: Promise<{ id: string }> }

export async function GET(req: NextRequest, { params }: RouteParams) {
  const { id: rawId } = await params
  const sessionId = decodeURIComponent(rawId || '').trim()
  if (!sessionId || !SESSION_RE.test(sessionId)) {
    return NextResponse.json({ error: 'invalid session id' }, { status: 400 })
  }

  const root = repoRoot()
  const script = join(root, 'scripts', 'web', 'zip_session.py')
  if (!existsSync(script)) {
    return NextResponse.json(
      { error: `zip_session.py が見つかりません（repo=${root}）` },
      { status: 503 },
    )
  }

  const listOnly =
    req.nextUrl.searchParams.get('list') === '1' ||
    req.nextUrl.searchParams.get('list') === 'true'

  if (listOnly) {
    const result = await runPython([script, sessionId, '-', '--list-only', '--json'])
    const data = parsePythonJson(result.stdout)
    if (!data || data.ok === false) {
      return NextResponse.json(
        {
          error: (data?.error as string) || result.stderr || 'list failed',
          session_id: sessionId,
        },
        { status: 404 },
      )
    }
    return NextResponse.json(data, {
      headers: { 'Cache-Control': 'no-store' },
    })
  }

  const zipPath = join(tmpdir(), `wpai-session-${sessionId}-${randomBytes(4).toString('hex')}.zip`)
  try {
    const result = await runPython([script, sessionId, zipPath, '--json'])
    const meta = parsePythonJson(result.stdout)
    if (result.code !== 0 || !meta || meta.ok === false || !existsSync(zipPath)) {
      return NextResponse.json(
        {
          error: (meta?.error as string) || result.stderr || result.stdout || 'zip failed',
          session_id: sessionId,
          code: result.code,
        },
        { status: 404 },
      )
    }

    const buf = readFileSync(zipPath)
    const filename = `wpai-session-${sessionId}.zip`
    return new NextResponse(buf, {
      status: 200,
      headers: {
        'Content-Type': 'application/zip',
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Content-Length': String(buf.length),
        'Cache-Control': 'no-store',
        'X-Session-Id': sessionId,
        'X-File-Count': String(meta.file_count ?? ''),
      },
    })
  } finally {
    if (existsSync(zipPath)) {
      try {
        unlinkSync(zipPath)
      } catch {
        // ignore
      }
    }
  }
}
