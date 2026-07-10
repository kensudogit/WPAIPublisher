import { AppShell } from '@/components/AppShell'
import { HtmlSelectPanel } from '@/components/HtmlSelectPanel'

export default function PipelinePage() {
  return (
    <AppShell>
      <h1 className="page-title">HTML 選択 → パイプライン</h1>
      <p className="page-lead">
        複数の HTML が入ったフォルダから処理対象を選び、intake 作成から convert prepare まで実行します。
        Railway 上ではローカルパスではなく、フォルダのアップロードまたはサンプル一覧を使います。
      </p>

      <div className="panel">
        <div className="panel-head">
          <h2>ファイル選択</h2>
        </div>
        <div className="panel-body">
          <HtmlSelectPanel />
        </div>
      </div>
    </AppShell>
  )
}
