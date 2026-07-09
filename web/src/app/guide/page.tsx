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
            ローカル確認は <code>docker compose -f docker-compose.staging.yml up -d</code> のあと、
            <code>python wpaipublish.py deploy staging &lt;session&gt;</code> で反映できます。
          </p>
          <p>
            詳細ドキュメント: <code>docs/LOCAL_STAGING.md</code> · <code>docs/FEATURES.md</code> ·{' '}
            <code>docs/OPERATIONS.md</code>
          </p>
        </div>
        <UsageGuidePanel />
      </div>
    </AppShell>
  )
}
