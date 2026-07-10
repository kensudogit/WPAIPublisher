'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

const techStack = [
  'Python · CLI',
  'Claude Code',
  'SWELL',
  'WP-CLI · REST',
  'Playwright',
  'Git · Actions',
] as const

const archDiagram = `Codex / ChatGPT / Copilot
    │ HTML · CSS · JS
    ▼
analyze → structure.json   コンポーネント抽出
    │
    ▼
SWELL convert              子テーマ / blocks / parts
    │ output/<session>/
    ▼
deploy + Playwright差分    visual/diff/
    │
    ▼
git commit/push + report   change_report.md`

const recommendedFlow = [
  '初回のみ: knowledge index --rebuild + ローカル Docker staging',
  'SWELL一括: swell pipeline <id> --source-dir <folder> --select a.html --visual-update',
  'または: intake pipeline → agent run → Claude Code → agent resume',
  '確認: localhost:8088 / change_report.md',
  'git commit <id> --push → 本番は --approve / --confirm',
] as const

const steps = [
  {
    title: '0. 推奨フロー（最短・安全）',
    body: 'SWELL は swell pipeline 一括、汎用 WP は Agent + Claude Code。先にローカル staging で確認します。',
    items: [...recommendedFlow],
  },
  {
    title: '1. 初回セットアップ',
    body: '依存関係と設定ファイルを用意します。リモート WP がなくても Docker で完走できます。',
    items: [
      'pip install -r requirements.txt',
      'npm install && npx playwright install chromium',
      'config/*.example.yaml をコピーして編集',
      'config/.env に WP / API キー（ローカルのみなら後回し可）',
      'docker compose -f docker-compose.staging.yml up -d',
      'bash scripts/local/bootstrap_wp.sh（初回のみ）',
    ],
  },
  {
    title: '2. ナレッジベース構築',
    body: '変換前に RAG を用意すると、Claude Code の出力品質が安定します。',
    items: [
      'python wpaipublish.py knowledge index --rebuild',
      'セッション追加: knowledge index --session <id>',
      '変換前: knowledge retrieve --session <id>',
    ],
  },
  {
    title: '3. AI出力の投入',
    body: '単一パッケージ、または複数 HTML から選択して intake します。',
    items: [
      '単一: intake/incoming/<package>/ + manifest.json',
      '検証: python wpaipublish.py intake validate ...',
      '複数HTML: intake list / select / pipeline',
      'Web UI: /pipeline でチェック選択 → 開始',
      'セッションIDは日付付き短名を推奨（例: hero-20260710）',
    ],
  },
  {
    title: '3b. 複数HTMLから選択',
    body: 'フォルダ内の HTML を一覧し、処理対象だけをパイプラインへ流します。',
    items: [
      'python wpaipublish.py intake list <folder>',
      'intake select <folder> --interactive',
      'intake pipeline <folder> --select a.html --session-id <id>',
      '同名 CSS/JS・相対参照アセットは自動同梱',
      'サンプル: intake/samples/multi-html/',
    ],
  },
  {
    title: '4. Claude Code で変換',
    body: 'WP向け変換はコード手書き不要。Agent 経由が手数が最少です。',
    items: [
      '推奨: agent run <id> → 指示ファイルを Claude Code で実行',
      '代替: convert prepare → Claude Code → convert mark-done',
      '任意: ai route --stage wp_conversion --auto-cli',
      '出力: output/<session>/wordpress/',
      '注意: intake〜deploy 全体は CLI 必須（設定だけでは不可）',
    ],
  },
  {
    title: '5. 品質ゲート',
    body: 'blocking 失敗時はデプロイしない。初回 visual は --update が必要です。',
    items: [
      'agent resume で quality → visual → PR → staging まで進行',
      '手動: quality run / visual run --update（初回）',
      '結果: output/<session>/quality_gates.json',
    ],
  },
  {
    title: '6. ステージング確認',
    body: '本番前は必ず staging。ローカル Docker を先に使うと速いです。',
    items: [
      'deploy staging <session>（ローカルなら localhost:8088）',
      '確認: レスポンシブ · JS · 既存ページ影響 · コンソール',
      'レビュー: prompts/deploy-review.md',
    ],
  },
  {
    title: '7. 本番デプロイ',
    body: '確認後に --confirm または agent --approve で本番反映します。',
    items: [
      'agent resume <session> --approve',
      'または deploy production <session> --confirm',
      '障害時は rollback --confirm',
      '処理済み intake は intake/processed/ へ移動',
    ],
  },
  {
    title: '8. テスト（品質確認）',
    body: 'ユニットテストを実行し、結果を Web の /tests で確認します。',
    items: [
      'python wpaipublish.py test run',
      'test list / test show latest',
      'Web: /tests で実行・履歴・ケース詳細',
      '結果保存先: output/test-results/',
    ],
  },
  {
    title: '9. SWELL 一連パイプライン',
    body: '解析→SWELL変換→デプロイ→Playwright差分→Git→変更レポートを一括実行します。',
    items: [
      'swell pipeline <id> --source-dir <folder> --select a.html --visual-update',
      'analyze → structure.json（構造・コンポーネント抽出）',
      'swell convert → 子テーマ / blocks / template-parts',
      'deploy staging → visual run（pixelmatch 差分）',
      'git commit <id> --push（任意 --pr）',
      'report generate → change_report.md',
      'Web: /swell · 詳細: docs/SWELL.md',
    ],
  },
] as const

export function UsageGuidePanel() {
  const panelRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<{
    pointerId: number
    startX: number
    startY: number
    originX: number
    originY: number
  } | null>(null)

  const [expanded, setExpanded] = useState(true)
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const [dragging, setDragging] = useState(false)

  const onHeaderPointerDown = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if ((e.target as HTMLElement).closest('.usage-guide-toggle')) return
      if (!pos) return
      dragRef.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        originX: pos.x,
        originY: pos.y,
      }
      setDragging(true)
      e.currentTarget.setPointerCapture(e.pointerId)
    },
    [pos],
  )

  const onHeaderPointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== e.pointerId) return
    setPos({
      x: drag.originX + (e.clientX - drag.startX),
      y: drag.originY + (e.clientY - drag.startY),
    })
  }, [])

  const onHeaderPointerUp = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== e.pointerId) return
    dragRef.current = null
    setDragging(false)
    e.currentTarget.releasePointerCapture(e.pointerId)
  }, [])

  useEffect(() => {
    // 初期は通常フロー配置。ドラッグ開始後に fixed 化
  }, [])

  const style =
    pos != null
      ? ({
          position: 'fixed' as const,
          left: pos.x,
          top: pos.y,
          width: 420,
          zIndex: 40,
          margin: 0,
        } as const)
      : undefined

  return (
    <div
      ref={panelRef}
      className={`usage-guide-panel${expanded ? '' : ' is-collapsed'}${dragging ? ' is-dragging' : ''}`}
      style={style}
      role="dialog"
      aria-label="利用手順"
      aria-modal="false"
    >
      <header
        className="usage-guide-header"
        onPointerDown={(e) => {
          if (pos == null && panelRef.current) {
            const rect = panelRef.current.getBoundingClientRect()
            setPos({ x: rect.left, y: rect.top })
            dragRef.current = {
              pointerId: e.pointerId,
              startX: e.clientX,
              startY: e.clientY,
              originX: rect.left,
              originY: rect.top,
            }
            setDragging(true)
            e.currentTarget.setPointerCapture(e.pointerId)
            return
          }
          onHeaderPointerDown(e)
        }}
        onPointerMove={onHeaderPointerMove}
        onPointerUp={onHeaderPointerUp}
        onPointerCancel={onHeaderPointerUp}
      >
        <div className="usage-guide-header-text">
          <span aria-hidden>☰</span>
          <div className="usage-guide-header-titles">
            <strong>利用手順</strong>
            <span className="usage-guide-header-sub">Architecture &amp; Ops</span>
          </div>
          <span className="usage-guide-drag-hint">ドラッグで移動</span>
        </div>
        <button
          type="button"
          className="usage-guide-toggle"
          aria-label={expanded ? '閉じる' : '開く'}
          aria-expanded={expanded}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? '▼' : '▲'}
        </button>
      </header>

      {expanded ? (
        <div className="usage-guide-body">
          <div className="usage-guide-hero">
            <p className="usage-guide-hero-kicker">Portfolio-ready demo</p>
            <h2 className="usage-guide-hero-title">WPAIPublisher AI → WordPress</h2>
            <p className="usage-guide-hero-lead">
              Codex / ChatGPT / Claude Code / Copilot の出力を、品質ゲート・Git CI/CD・RAG・自律エージェント経由で
              WordPress へ継続反映する再現可能なワークフローです。
            </p>
            <div className="usage-guide-stack" aria-label="Tech stack">
              {techStack.map((tag) => (
                <span key={tag} className="usage-guide-stack-pill">
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <section className="usage-guide-featured" aria-label="パイプライン概要">
            <div className="usage-guide-featured-head">
              <span className="usage-guide-featured-badge">Architecture</span>
              <strong>エンドツーエンド・パイプライン</strong>
            </div>
            <p>
              AI 出力を intake で受け取り、マルチ AI 変換 → 品質ゲート → ビジュアル回帰 → Git PR → ステージング →
              本番までを一連で実行します。
            </p>
          </section>

          <section className="usage-guide-featured" aria-label="推奨フロー">
            <div className="usage-guide-featured-head">
              <span className="usage-guide-featured-badge">Recommended</span>
              <strong>最短・安全な進め方</strong>
            </div>
            <p>
              手作業のコマンド列より、<code>swell pipeline</code>（解析〜レポート一括）または{' '}
              <code>intake pipeline</code> → <code>agent run</code> → Claude Code → <code>agent resume</code>{' '}
              の方がミスが少なく、品質ゲートも飛ばしにくいです。リモート WP の前にローカル Docker staging
              で確認してください。
            </p>
            <ul className="usage-guide-items">
              {recommendedFlow.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <figure className="usage-guide-diagram" aria-label="Service topology">
            <figcaption>Service topology（本番）</figcaption>
            <pre>{archDiagram}</pre>
          </figure>

          <p className="usage-guide-scroll-hint">↓ セットアップから本番までの手順</p>

          <ol className="usage-guide-steps">
            {steps.map((step) => (
              <li key={step.title}>
                <strong>{step.title}</strong>
                <p>{step.body}</p>
                <ul className="usage-guide-items">
                  {step.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>

          <p className="usage-guide-footer">
            ▼▲ で開閉 · ヘッダーをドラッグして移動 · SWELL は /swell · docs/SWELL.md · テストは /tests
          </p>
        </div>
      ) : null}
    </div>
  )
}
