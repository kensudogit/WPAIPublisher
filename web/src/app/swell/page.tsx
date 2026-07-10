import { AppShell } from '@/components/AppShell'
import { SwellPipelinePanel } from '@/components/SwellPipelinePanel'

export default function SwellPage() {
  return (
    <AppShell>
      <h1 className="page-title">SWELL パイプライン</h1>
      <p className="page-lead">
        HTML 解析 → SWELL 子テーマ／ブロック／テンプレート変換 → デプロイ → Playwright 差分 → 変更レポートまでを実行します。
        クラウド上ではローカルパスではなく、フォルダのアップロードまたはサンプル実行を使います。
        WordPress への反映は利用手順の「9b」または <code>docs/SWELL.md</code> を参照してください。
      </p>
      <div className="panel">
        <div className="panel-head">
          <h2>実行</h2>
        </div>
        <div className="panel-body">
          <SwellPipelinePanel />
        </div>
      </div>
    </AppShell>
  )
}
