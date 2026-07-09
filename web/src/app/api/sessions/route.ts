import { readdir, readFile, stat } from 'fs/promises'
import { join } from 'path'
import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

type Session = {
  id: string
  status: string
  agent: string
  target: string
  staging_url?: string | null
  production_url?: string | null
  updated_at?: string | null
}

async function readFromPostgres(): Promise<Session[] | null> {
  const url = process.env.DATABASE_URL
  if (!url) return null

  try {
    const { default: pg } = await import('pg')
    const client = new pg.Client({
      connectionString: url,
      ssl: process.env.PGSSLMODE === 'disable' ? false : { rejectUnauthorized: false },
    })
    await client.connect()
    try {
      await client.query(`
        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY,
          status TEXT NOT NULL DEFAULT 'unknown',
          agent TEXT NOT NULL DEFAULT '-',
          target TEXT NOT NULL DEFAULT '?',
          staging_url TEXT,
          production_url TEXT,
          notes TEXT,
          manifest JSONB,
          task JSONB,
          created_at TIMESTAMPTZ,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `)
      const result = await client.query(
        `SELECT id, status, agent, target, staging_url, production_url, updated_at
         FROM sessions
         ORDER BY updated_at DESC
         LIMIT 100`,
      )
      return result.rows.map((r) => ({
        id: r.id,
        status: r.status,
        agent: r.agent,
        target: r.target,
        staging_url: r.staging_url,
        production_url: r.production_url,
        updated_at: r.updated_at ? new Date(r.updated_at).toISOString() : null,
      }))
    } finally {
      await client.end()
    }
  } catch (e) {
    console.error('[sessions] postgres error:', e)
    return null
  }
}

async function readFromFilesystem(): Promise<Session[]> {
  const candidates = [
    join(process.cwd(), '..', 'output'),
    join(process.cwd(), 'output'),
    '/output',
  ]

  let outputDir = ''
  for (const dir of candidates) {
    try {
      const st = await stat(dir)
      if (st.isDirectory()) {
        outputDir = dir
        break
      }
    } catch {
      // try next
    }
  }
  if (!outputDir) return []

  const entries = await readdir(outputDir)
  const sessions: (Session & { mtime: number })[] = []

  for (const name of entries) {
    if (name.startsWith('.')) continue
    const dir = join(outputDir, name)
    const st = await stat(dir).catch(() => null)
    if (!st?.isDirectory()) continue

    let status = 'unknown'
    let target = '?'
    let agent = '-'
    let staging_url: string | null = null

    try {
      const task = JSON.parse(await readFile(join(dir, 'task.json'), 'utf-8')) as {
        status?: string
        staging_url?: string
        manifest?: { target?: { type?: string } }
      }
      status = task.status ?? status
      target = task.manifest?.target?.type ?? target
      staging_url = task.staging_url ?? null
    } catch {
      status = 'no task'
    }

    try {
      const agentState = JSON.parse(await readFile(join(dir, 'agent_state.json'), 'utf-8')) as {
        status?: string
      }
      agent = agentState.status ?? agent
    } catch {
      // optional
    }

    sessions.push({ id: name, status, agent, target, staging_url, mtime: st.mtimeMs })
  }

  sessions.sort((a, b) => b.mtime - a.mtime)
  return sessions.map(({ mtime: _m, ...rest }) => rest)
}

export async function GET() {
  const fromDb = await readFromPostgres()
  if (fromDb) {
    return NextResponse.json({ sessions: fromDb, source: 'postgres' })
  }
  const sessions = await readFromFilesystem()
  return NextResponse.json({ sessions, source: 'filesystem' })
}
