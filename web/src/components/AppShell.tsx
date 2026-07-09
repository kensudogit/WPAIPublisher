'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const links = [
  { href: '/', label: 'ホーム' },
  { href: '/dashboard', label: 'ダッシュボード' },
  { href: '/pipeline', label: 'HTML選択' },
  { href: '/guide', label: '利用手順' },
] as const

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <strong>WPAIPublisher</strong>
          <span>AI → WordPress Console</span>
        </div>
        <nav className="nav" aria-label="メイン">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname === link.href ? 'page' : undefined}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </header>
      {children}
    </div>
  )
}
