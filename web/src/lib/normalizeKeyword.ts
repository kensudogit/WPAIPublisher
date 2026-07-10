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
