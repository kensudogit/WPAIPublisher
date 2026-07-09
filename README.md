# WPAIPublisher

Codex / ChatGPT / Claude Code / GitHub Copilot 等の AI コーディングツールが出力する HTML / CSS / JavaScript を、WordPress サイトへ継続的に実装・反映するためのワークフローパッケージです。

## 標準装備機能

| 機能 | 説明 |
|------|------|
| **マルチAI対応** | ChatGPT, Codex, Claude Code, Copilot をステージごとに最適配置 |
| **品質ゲート** | HTML / SEO / アクセシビリティ / セキュリティ / パフォーマンスの自動検査 |
| **Git CI/CD** | Pull Request → ステージング → 本番 → ロールバック |
| **ビジュアル回帰テスト** | Playwright による画面比較 |
| **ナレッジ再利用（RAG）** | 過去の変換パターンをベクトル検索で再利用 |
| **AIエージェント** | 要件整理からデプロイまでの自律実行 |

詳細: [docs/FEATURES.md](docs/FEATURES.md)

## 概要

```
AI出力 (Codex/ChatGPT等)
    ↓ intake/incoming/
バリデーション + RAGナレッジ検索
    ↓
マルチAI変換 (Claude Code等)
    ↓ output/<session>/
品質ゲート + ビジュアル回帰テスト
    ↓
Git PR → CI → ステージングデプロイ → 確認 → 本番デプロイ
```

## ディレクトリ構成

```
WPAIPublisher/
├── wpaipublish.py              # メインオーケストレーター
├── package.json                # Playwright等（Node.js）
├── workflow/pipeline.yaml      # AIエージェントパイプライン定義
├── config/
│   ├── environments.example.yaml
│   ├── ai-providers.example.yaml
│   ├── quality-gates.example.yaml
│   └── .env.example
├── intake/                     # AI出力の投入先
├── output/<session-id>/        # 変換セッション
├── knowledge/                  # RAGナレッジベース
├── deployments/                # デプロイ履歴・バックアップ
├── prompts/                    # AI用プロンプト（マルチAI対応）
├── scripts/
│   ├── ai/                     # マルチAIルーター
│   ├── quality/                # 品質ゲート
│   ├── visual/                 # ビジュアル回帰テスト
│   ├── knowledge/              # RAG
│   ├── git/                    # Git CI/CD
│   ├── agent/                  # 自律エージェント
│   ├── intake/ convert/ validate/ deploy/ rollback/
│   └── lib/
├── .github/workflows/          # GitHub Actions CI/CD
└── docs/
    ├── FEATURES.md             # 拡張機能ガイド
    ├── OPERATIONS.md
    └── ROLLBACK.md
```

## クイックスタート

### 1. セットアップ

```bash
cd WPAIPublisher
pip install -r requirements.txt
npm install && npx playwright install chromium

cp config/environments.example.yaml config/environments.yaml
cp config/ai-providers.example.yaml config/ai-providers.yaml
cp config/quality-gates.example.yaml config/quality-gates.yaml
cp config/.env.example config/.env
# 各ファイルを編集
```

### 2. ナレッジベース構築

```bash
python wpaipublish.py knowledge index --rebuild
```

### 3. AI出力の投入

```bash
cp -r intake/example intake/incoming/hero-demo
python wpaipublish.py intake validate intake/incoming/hero-demo
```

### 4. エージェント自律実行（推奨）

```bash
python wpaipublish.py convert prepare intake/incoming/hero-demo --session-id my-session
python wpaipublish.py agent run my-session
# 手動変換完了後: python wpaipublish.py agent resume my-session
# 本番承認: python wpaipublish.py agent resume my-session --approve
```

### 5. 手動ステップ実行

```bash
python wpaipublish.py convert prepare intake/incoming/hero-demo
python wpaipublish.py ai route --stage wp_conversion --session <session-id>
python wpaipublish.py convert mark-done <session-id>
python wpaipublish.py quality run <session-id>
python wpaipublish.py visual run <session-id> --update
python wpaipublish.py git pr <session-id>
python wpaipublish.py deploy staging <session-id>
python wpaipublish.py deploy production <session-id> --confirm
```

### 6. ステータス確認

```bash
python wpaipublish.py status
```

## CLI コマンド一覧

| コマンド | 説明 |
|---------|------|
| `intake validate` | AI出力バリデーション |
| `convert prepare / mark-done` | 変換セッション管理 |
| `validate run` | 基本検証（PHP構文等） |
| `quality run` | 品質ゲート（5種） |
| `visual run` | ビジュアル回帰テスト |
| `git pr / deploy / rollback` | Git CI/CD |
| `knowledge index / retrieve` | RAGナレッジベース |
| `ai route / list` | マルチAIルーター |
| `agent run / resume` | AIエージェント自律実行 |
| `deploy / rollback` | 直接デプロイ・ロールバック |
| `status` | セッション一覧 |

## 前提条件

| ツール | 用途 |
|--------|------|
| Python 3.10+ | スクリプト実行 |
| Node.js 18+ | Playwright, axe-core |
| Bash | デプロイ・ロールバック |
| WP-CLI | サーバー上のWordPress操作 |
| SSH / SCP | リモートファイル同期 |
| Git + gh CLI | PR作成・CI/CD |
| AI ツール | ChatGPT API / Claude Code / Copilot 等 |

## ドキュメント

- [利用手順パネル（UI）](docs/usage-guide.html) — アップロード画像と同デザインの詳細手順
- [拡張機能ガイド](docs/FEATURES.md)
- [運用マニュアル](docs/OPERATIONS.md)
- [ロールバック手順書](docs/ROLLBACK.md)

## ライセンス

MIT
# WPAIPublisher
