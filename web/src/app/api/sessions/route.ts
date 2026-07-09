import { readdir, readFile, stat } from 'fs/promises'
import { join } from 'path'
import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

type Session = {
  id: string
  status: string
  agent: string
  target: string
}

type SessionRow = Session & { mtime: number }

async function readSessions(): Promise<Session[]> {
  const outputDir = join(process.cwd(), '..', 'output')
  let entries: string[] = []
  try {
    entries = await readdir(outputDir)
  } catch {
    return []
  }

  const sessions: SessionRow[] = []
  for (const name of entries) {
    if (name.startsWith('.')) continue
    const dir = join(outputDir, name)
    const st = await stat(dir).catch(() => null)
    if (!st?.isDirectory()) continue

    let status = 'unknown'
    let target = '?'
    let agent = '-'

    try {
      const task = JSON.parse(await readFile(join(dir, 'task.json'), 'utf-8')) as {
        status?: string
        manifest?: { target?: { type?: string } }
      }
      status = task.status ?? status
      target = task.manifest?.target?.type ?? target
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

    sessions.push({ id: name, status, agent, target, mtime: st.mtimeMs })
  }

  sessions.sort((a, b) => b.mtime - a.mtime)
  return sessions.map(({ mtime: _m, ...rest }) => rest)
}

export async function GET() {
  const sessions = await readSessions()
  return NextResponse.json({ sessions })
}
