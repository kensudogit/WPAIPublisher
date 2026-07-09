import Link from 'next/link'
import { AppShell } from '@/components/AppShell'

const features = [
  {
    title: 'マルチAI',
    body: 'ChatGPT / Codex / Claude Code / Copilot をステージごとに最適配置します。',
  },
  {
    title: '品質ゲート',
    body: 'HTML · SEO · a11y · セキュリティ · パフォーマンスを自動検査します。',
  },
  {
    title: 'ローカル確認',
    body: 'Docker WordPress でステージング反映まで完走できます。',
  },
] as const

export default function HomePage() {
  return (
    <AppShell>
      <section className="hero" aria-label="WPAIPublisher">
        <div className="hero-inner">
          <p className="hero-kicker">AI Coding → WordPress</p>
          <h1>WPAIPublisher</h1>
          <p>
            AI が出力した HTML / CSS / JS を、検証・ステージング・本番反映までつなぐ再現可能なワークフローです。
          </p>
          <div className="cta-row">
            <Link className="btn btn-primary" href="/dashboard">
              ダッシュボードへ
            </Link>
            <Link className="btn btn-ghost" href="/guide">
              利用手順を見る
            </Link>
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="features-title">
        <div className="section-head">
          <h2 id="features-title">標準装備</h2>
          <p>変換からデプロイまで、運用に必要な仕組みを最初から同梱しています。</p>
        </div>
        <div className="feature-grid">
          {features.map((f) => (
            <article key={f.title} className="feature">
              <strong>{f.title}</strong>
              <p>{f.body}</p>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  )
}
