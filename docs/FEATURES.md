# WPAIPublisher 拡張機能ガイド

## 1. マルチAI対応

複数のAIツールをパイプラインの各ステージに割り当て可能。

### 設定

```bash
cp config/ai-providers.example.yaml config/ai-providers.yaml
```

### プロバイダー一覧

| プロバイダー | 用途 | 接続方式 |
|-------------|------|---------|
| ChatGPT | intake整形、フォールバック | OpenAI API |
| Codex | HTML/CSS/JS生成 | OpenAI API |
| Claude Code | WP変換、レビュー | CLI / IDE |
| GitHub Copilot | 補助的なコード整形 | IDE手動 |

### コマンド

```bash
# プロバイダー一覧と利用可否
python wpaipublish.py ai list

# 特定ステージをAIにルーティング
python wpaipublish.py ai route --stage wp_conversion --session demo-20260709
```

---

## 2. 品質ゲート

HTML / SEO / アクセシビリティ / セキュリティ / パフォーマンスの自動検査。

### 設定

```bash
cp config/quality-gates.example.yaml config/quality-gates.yaml
```

### コマンド

```bash
python wpaipublish.py quality run <session_id> --stage pr_merge
```

### ゲート一覧

| ゲート | 検査内容 | デフォルト |
|--------|---------|-----------|
| html | 禁止タグ、lang属性、インラインスタイル | blocking |
| seo | title, meta, h1, alt | warning |
| accessibility | alt, ラベル, axe-core | blocking |
| security | 危険関数、未エスケープ出力 | blocking |
| performance | CSS/JSサイズ、インラインscript | warning |

結果は `output/<session>/quality_gates.json` に保存。

---

## 3. Gitベース CI/CD

Pull Request → ステージング → 本番の Git フロー。

### ワークフロー

```
feature branch (wpai/<session>)
    → PR (staging へ)
    → CI (品質ゲート + ビジュアル回帰)
    → merge to staging → ステージング自動デプロイ
    → 確認後 merge to main → 本番自動デプロイ
```

### コマンド

```bash
# PR作成
python wpaipublish.py git pr <session_id>

# Gitベースデプロイ
python wpaipublish.py git deploy staging <session_id>
python wpaipublish.py git deploy production <session_id> --confirm

# Gitロールバック
python wpaipublish.py git rollback <session_id> production --confirm
```

### GitHub Actions

`.github/workflows/wpaipublisher-ci.yml` が PR/push 時に自動実行。

必要な Secrets:
- `WP_STAGING_URL`, `WP_STAGING_SSH`, `WP_STAGING_PATH`
- `WP_PROD_SSH`, `WP_PROD_PATH`

---

## 4. ビジュアル回帰テスト

Playwright による画面比較。

### セットアップ

```bash
npm install
npx playwright install chromium
```

### コマンド

```bash
# テスト実行
python wpaipublish.py visual run <session_id> --env staging

# ベースライン更新
python wpaipublish.py visual run <session_id> --update
```

スクリーンショット保存先:
- `output/<session>/visual/baseline/` — 基準画像
- `output/<session>/visual/current/` — 今回の画像
- `output/<session>/visual/diff/` — 差分（失敗時）

---

## 5. ナレッジ再利用（RAG）

過去の変換パターン・プロンプト・ドキュメントをベクトル検索で再利用。

### インデックス作成

```bash
python wpaipublish.py knowledge index --rebuild
python wpaipublish.py knowledge index --session <session_id>
```

### 検索（変換前に自動実行）

```bash
python wpaipublish.py knowledge retrieve --session <session_id>
```

結果は `output/<session>/rag_context.md` に保存され、AI変換時に参照される。

### ストレージ

- ローカル TF-IDF ベクトルストア: `knowledge/vector_store/`
- オプションで ChromaDB / OpenAI Embeddings に拡張可能

---

## 6. AIエージェント自律実行

要件整理からデプロイまでの一連を自動化。

### パイプライン定義

`workflow/pipeline.yaml` でステージを定義。

### コマンド

```bash
# パイプライン一覧（ドライラン）
python wpaipublish.py agent run <session_id> --dry-run

# 自律実行開始
python wpaipublish.py agent run <session_id>

# 手動ステージ完了後に再開
python wpaipublish.py agent resume <session_id>

# 本番デプロイ承認して再開
python wpaipublish.py agent resume <session_id> --approve
```

### 中断ポイント

| ステージ | 理由 |
|---------|------|
| wp_conversion | Claude Code 手動変換 |
| deploy_review | デプロイ前レビュー |
| deploy_production | 本番承認必須 |

状態は `output/<session>/agent_state.json` に記録。

---

## 推奨ワークフロー（全機能統合）

```bash
# 1. 初期セットアップ
pip install -r requirements.txt && npm install
cp config/*.example.yaml config/  # 各yamlをコピーして編集
cp config/.env.example config/.env

# 2. ナレッジベース構築
python wpaipublish.py knowledge index --rebuild

# 3. intake投入・検証
python wpaipublish.py intake validate intake/incoming/my-package

# 4. エージェント自律実行（変換〜PRまで）
python wpaipublish.py convert prepare intake/incoming/my-package --session-id my-session
python wpaipublish.py agent run my-session

# 5. 手動変換完了後
python wpaipublish.py agent resume my-session

# 6. 本番承認
python wpaipublish.py agent resume my-session --approve
```
