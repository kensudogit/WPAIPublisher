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
            手順パネルの「0」「9」「9b」を参照。
          </p>
          <p>
            複数 HTML が入ったフォルダから処理対象を選ぶ場合は、ナビの「HTML選択」(<code>/pipeline</code>)、または
            <code>intake list / select / pipeline</code> を使います。手順パネルの「3b」も参照してください。
          </p>
          <p>
            SWELL 子テーマ変換・変更レポートはナビの「SWELL」(<code>/swell</code>)。成果物を WordPress へ反映する手順は
            手順パネルの「9b」と <code>docs/SWELL.md</code>（WordPress への反映手順）を参照してください。
          </p>
          <p>
            WordPress 向け変換（Claude Code 経路）はプロンプトに従うだけでよく、コードの手書きは不要です。
            ただし intake〜品質ゲート〜デプロイの一連処理は CLI が必要です（手順パネルの「4」）。
          </p>
          <p>
            ローカル確認は <code>docker compose -f docker-compose.staging.yml up -d</code> のあと、
            <code>python wpaipublish.py deploy staging &lt;session&gt;</code> で
            <code>staging/wp-content/themes/swell-child/</code> へ反映できます（確認: http://localhost:8088）。
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
