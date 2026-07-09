import { AppShell } from '@/components/AppShell'
import { SessionTable } from '@/components/SessionTable'

const flow = [
  {
    title: 'Intake',
    body: 'AI出力を manifest.json 付きで受け取り、バリデーションします。',
  },
  {
    title: 'Convert',
    body: 'Claude Code 等で WordPress ブロック / テーマへ変換します。',
  },
  {
    title: 'Quality',
    body: '品質ゲートと Playwright ビジュアル回帰で合否を判定します。',
  },
  {
    title: 'Deploy',
    body: 'ローカル Docker またはリモート staging / production へ反映します。',
  },
] as const

export default function DashboardPage() {
  return (
    <AppShell>
      <h1 className="page-title">ダッシュボード</h1>
      <p className="page-lead">
        セッション状態とパイプラインの流れを確認します。データはリポジトリの <code>output/</code> から読み込みます。
      </p>

      <div className="panel" style={{ marginBottom: '1.5rem' }}>
        <div className="panel-head">
          <h2>セッション一覧</h2>
        </div>
        <div className="panel-body">
          <SessionTable />
        </div>
      </div>

      <section className="section" aria-labelledby="flow-title">
        <div className="section-head">
          <h2 id="flow-title">パイプライン</h2>
          <p>要件整理から本番反映までの標準フローです。</p>
        </div>
        <ol className="flow">
          {flow.map((item, i) => (
            <li key={item.title}>
              <span className="flow-step">{i + 1}</span>
              <div>
                <strong>{item.title}</strong>
                <p>{item.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </AppShell>
  )
}
