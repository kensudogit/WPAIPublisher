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
            <strong>推奨:</strong> SWELL 向けは <code>swell pipeline</code>（解析〜デプロイ〜Playwright〜レポート一括）。
            汎用 WP 変換は <code>intake pipeline</code> → <code>agent run</code> → Claude Code →{' '}
            <code>agent resume</code>。リモート WP の前に Docker の <code>localhost:8088</code> で確認してください。
            手順パネルの「0」「9」を参照。
          </p>
          <p>
            複数 HTML が入ったフォルダから処理対象を選ぶ場合は、ナビの「HTML選択」(<code>/pipeline</code>)、または
            <code>intake list / select / pipeline</code> を使います。手順パネルの「3b」も参照してください。
          </p>
          <p>
            SWELL 子テーマ変換・変更レポートはナビの「SWELL」(<code>/swell</code>)、詳細は{' '}
            <code>docs/SWELL.md</code>。
          </p>
          <p>
            WordPress 向け変換（Claude Code 経路）はプロンプトに従うだけでよく、コードの手書きは不要です。
            ただし intake〜品質ゲート〜デプロイの一連処理は CLI が必要です（手順パネルの「4」）。
          </p>
          <p>
            ローカル確認は <code>docker compose -f docker-compose.staging.yml up -d</code> のあと、
            <code>python wpaipublish.py deploy staging &lt;session&gt;</code> で反映できます。
          </p>
          <p>
            詳細ドキュメント: <code>docs/SWELL.md</code> · <code>docs/LOCAL_STAGING.md</code> ·{' '}
            <code>docs/FEATURES.md</code> · <code>docs/OPERATIONS.md</code> · <code>docs/usage-guide.html</code>
          </p>
        </div>
        <UsageGuidePanel />
      </div>
    </AppShell>
  )
}
