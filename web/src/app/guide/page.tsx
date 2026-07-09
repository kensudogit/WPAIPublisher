import { AppShell } from '@/components/AppShell'
import { UsageGuidePanel } from '@/components/UsageGuidePanel'

export default function GuidePage() {
  return (
    <AppShell>
      <div className="guide-layout">
        <div className="guide-copy">
          <h1>利用手順</h1>
          <p>
            右のパネルはドラッグで移動・開閉できる利用手順です。セットアップからローカルステージング、本番デプロイまでの流れをまとめています。
          </p>
          <p>
            <strong>推奨:</strong> <code>intake pipeline</code> → <code>agent run</code> → Claude Code（コード手書き不要）→{' '}
            <code>agent resume</code>。リモート WP の前に Docker の <code>localhost:8088</code> で確認してください。手順パネルの「0」が最短フローです。
          </p>
          <p>
            複数 HTML が入ったフォルダから処理対象を選ぶ場合は、ナビの「HTML選択」(<code>/pipeline</code>)、または
            <code>intake list / select / pipeline</code> を使います。手順パネルの「3b」も参照してください。
          </p>
          <p>
            WordPress 向け変換は Claude Code のプロンプトに従うだけでよく、コードの手書きは不要です。
            ただし intake〜品質ゲート〜デプロイの一連処理は CLI が必要です（手順パネルの「4」）。
          </p>
          <p>
            ローカル確認は <code>docker compose -f docker-compose.staging.yml up -d</code> のあと、
            <code>python wpaipublish.py deploy staging &lt;session&gt;</code> で反映できます。
          </p>
          <p>
            詳細ドキュメント: <code>docs/LOCAL_STAGING.md</code> · <code>docs/FEATURES.md</code> ·{' '}
            <code>docs/OPERATIONS.md</code> · <code>docs/usage-guide.html</code>
          </p>
        </div>
        <UsageGuidePanel />
      </div>
    </AppShell>
  )
}
