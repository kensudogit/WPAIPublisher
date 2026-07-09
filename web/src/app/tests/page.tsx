import { AppShell } from '@/components/AppShell'
import { TestResultsPanel } from '@/components/TestResultsPanel'

export default function TestsPage() {
  return (
    <AppShell>
      <h1 className="page-title">テスト結果</h1>
      <p className="page-lead">
        pytest のテストクラスを実行し、結果をここに表示します。CLI でも{' '}
        <code>python wpaipublish.py test run</code> が使えます。
      </p>
      <TestResultsPanel />
    </AppShell>
  )
}
