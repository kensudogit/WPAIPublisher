import { spawn } from 'child_process'
import { existsSync } from 'fs'
import { join } from 'path'

/** Railway / local 共通のリポジトリルート解決 */
export function repoRoot(): string {
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
      existsSync(join(dir, 'scripts', 'intake', 'select_files.py')) ||
      existsSync(join(dir, 'scripts', 'swell', 'run_pipeline.py'))
    ) {
      return dir
    }
  }
  return envRoot || '/workspace'
}

export function looksLikeWindowsPath(p: string): boolean {
  return /^[a-zA-Z]:[\\/]/.test(p) || p.startsWith('\\\\')
}

export function runPython(
  args: string[],
  cwd?: string,
): Promise<{ code: number; stdout: string; stderr: string }> {
  const root = cwd || repoRoot()
  return new Promise((resolve) => {
    const py = process.env.PYTHON_BIN || 'python3'
    const child = spawn(py, args, {
      cwd: root,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (d: Buffer) => {
      stdout += d.toString()
    })
    child.stderr.on('data', (d: Buffer) => {
      stderr += d.toString()
    })
    child.on('close', (code) => {
      resolve({ code: code ?? 1, stdout, stderr })
    })
    child.on('error', (err) => {
      resolve({
        code: 1,
        stdout,
        stderr: `${err}\nPython 実行環境が見つかりません（repo=${root}）。`,
      })
    })
  })
}
