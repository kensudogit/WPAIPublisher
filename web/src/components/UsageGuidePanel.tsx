'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

const techStack = [
  'Python · CLI',
  'Claude Code',
  'WP-CLI · REST',
  'Playwright',
  'Git · Actions',
  'RAG · TF-IDF',
] as const

const archDiagram = `Codex / ChatGPT / Copilot
    │ HTML · CSS · JS
    ▼
intake/incoming/          manifest.json
    │ validate + RAG
    ▼
Claude Code 変換          prompts/convert-to-wp.md
    │ output/<session>/
    ▼
品質ゲート + Playwright   quality_gates.json
    │
    ▼
Git PR → staging → main   WP-CLI / REST / SCP
    │
    ▼
WordPress Staging / Prod  ロールバック可`

const steps = [
  {
    title: '1. 初回セットアップ',
    body: '依存関係と設定ファイルを用意します。',
    items: [
      'pip install -r requirements.txt',
      'npm install && npx playwright install chromium',
      'config/*.example.yaml をコピーして編集',
      'config/.env に WP / API キーを設定',
    ],
  },
  {
    title: '2. ナレッジベース構築',
    body: '過去の変換パターンをインデックスします。',
    items: [
      'python wpaipublish.py knowledge index --rebuild',
      'knowledge retrieve --session <id>',
    ],
  },
  {
    title: '3. AI出力の投入',
    body: 'Codex 等の成果物を intake 形式で受け取ります。',
    items: [
      'intake/incoming/<package>/ に配置',
      'manifest.json 必須',
      'python wpaipublish.py intake validate ...',
    ],
  },
  {
    title: '4. 変換〜品質ゲート',
    body: 'Claude Code で WP 向け変換し、自動検査します。',
    items: [
      'convert prepare / mark-done',
      'quality run / visual run',
    ],
  },
  {
    title: '5. ステージング確認',
    body: 'ローカル Docker またはリモート staging へ反映します。',
    items: [
      'docker compose -f docker-compose.staging.yml up -d',
      'python wpaipublish.py deploy staging <session>',
      'http://localhost:8088 で確認',
    ],
  },
  {
    title: '6. 本番デプロイ',
    body: '確認後に --confirm で本番反映します。',
    items: [
      'python wpaipublish.py deploy production <session> --confirm',
      '障害時は rollback --confirm',
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
            ▼▲ で開閉 · ヘッダーをドラッグして移動 · 詳細は docs/FEATURES.md · LOCAL_STAGING.md を参照。
          </p>
        </div>
      ) : null}
    </div>
  )
}
