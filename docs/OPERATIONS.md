# WPAIPublisher 運用マニュアル

## 1. 目的

本マニュアルは、WPAIPublisher を用いて AI 生成コードを WordPress サイトへ安全かつ再現性をもって反映するための運用手順を定めます。

### 拡張機能

マルチAI対応、品質ゲート、Git CI/CD、ビジュアル回帰テスト、RAG、AIエージェントの詳細は [FEATURES.md](FEATURES.md) を参照してください。

## 2. 役割分担

| 役割 | 担当 | 責務 |
|------|------|------|
| AI出力作成 | 開発者 / Codex / ChatGPT | HTML/CSS/JS の生成 |
| intake整形 | 開発者 / Copilot / ChatGPT | マニフェスト作成・ファイル整理 |
| WordPress変換 | Claude Code | WP向けコード変換 |
| 品質検査 | 自動品質ゲート + QA | HTML/SEO/a11y/security/perf |
| ビジュアル確認 | Playwright + QA | 画面回帰テスト |
| ステージング確認 | 開発者 / QA | 表示・動作確認 |
| 本番デプロイ | 開発者（承認者） | 本番反映の実行 |
| ロールバック | 開発者（承認者） | 障害時の復旧（Git/ファイル） |

## 3. 環境構成

### 3.1 ローカル（WPAIPublisher 実行環境）

- Python 3.10+
- Node.js 18+（Playwright, axe-core）
- Git + gh CLI
- SSH クライアント
- Claude Code（Cursor / CLI）
- OpenAI API Key（ChatGPT/Codex、任意）

### 3.2 ステージング

- 本番と同一の WordPress バージョン・PHP バージョン
- 本番と同一のテーマ・プラグイン構成
- WP-CLI インストール済み
- Application Passwords 有効

### 3.3 本番

- ステージングと同等構成
- デプロイ用 SSH キー認証
- バックアップ体制（ファイル + DB）

## 4. 初回セットアップ

### 4.1 設定ファイル

```bash
cp config/environments.example.yaml config/environments.yaml
cp config/.env.example config/.env
```

`config/.env` に以下を設定:

| 変数 | 説明 |
|------|------|
| `WP_STAGING_URL` | ステージングサイトURL |
| `WP_STAGING_USER` | REST API ユーザー名 |
| `WP_STAGING_APP_PASSWORD` | Application Password |
| `WP_STAGING_SSH` | SSH接続先（user@host） |
| `WP_STAGING_PATH` | WordPress ルートパス |
| `WP_PROD_*` | 本番環境（同上） |

### 4.2 Application Password の発行

1. WordPress 管理画面 → ユーザー → プロフィール
2. 「アプリケーションパスワード」で新規作成
3. 名前: `WPAIPublisher-deploy`
4. 生成されたパスワードを `.env` に設定

### 4.3 SSH 接続確認

```bash
ssh $WP_STAGING_SSH "cd $WP_STAGING_PATH && wp --info"
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp --info"
```

## 5. 標準ワークフロー

### 推奨: SWELL 一連パイプライン（解析〜レポート）

SWELL 子テーマ向けは次が一括で最短です。詳細は [SWELL.md](SWELL.md)。

```bash
# 初回のみ
python wpaipublish.py knowledge index --rebuild
docker compose -f docker-compose.staging.yml up -d
bash scripts/local/bootstrap_wp.sh   # Git Bash / WSL
npm install   # pixelmatch / pngjs（Playwright 差分）

# 解析 → SWELL変換 → validate → deploy → visual → report
python wpaipublish.py swell pipeline swell-demo \
  --source-dir intake/samples/multi-html \
  --select hero.html \
  --visual-update

# Git コミット & プッシュ（任意で --pr）
python wpaipublish.py git commit swell-demo --push

# レポート再生成
python wpaipublish.py report generate swell-demo
# → output/swell-demo/change_report.md
```

Web: `/swell`

### 推奨: 汎用 WP（Agent + ローカル staging）

Claude Code で汎用ブロック／テーマへ変換する場合:

```bash
python wpaipublish.py intake pipeline intake/samples/multi-html \
  --select hero.html \
  --session-id hero-20260710 \
  --target-type page

python wpaipublish.py agent run hero-20260710
# … Claude Code で CLAUDE_INSTRUCTIONS.md / convert-to-wp.md を実行 …
python wpaipublish.py convert mark-done hero-20260710
python wpaipublish.py agent resume hero-20260710
# http://localhost:8088 で確認
python wpaipublish.py agent resume hero-20260710 --approve
```

**運用のコツ**

| コツ | 理由 |
|------|------|
| セッションIDは日付付き短名 | 追跡・ロールバックが容易 |
| 変換前に `knowledge retrieve` | RAG で変換品質が安定 |
| 先にローカル Docker staging | リモート設定前でも完走できる |
| 初回 `visual run --update` | ベースラインがないと比較できない |
| blocking 失敗時はデプロイしない | 修正 → mark-done → resume |
| 処理済みは `intake/processed/` へ | 二重投入防止 |

### Phase 1: AI出力の受け取り

**頻度**: AI生成のたびに実施

#### 単一パッケージ

1. Codex 等で HTML/CSS/JS を生成
2. `intake/incoming/<package-name>/` にファイルを配置
3. `manifest.json` を作成（`intake/example/` 参照）
4. バリデーション実行:

```bash
python wpaipublish.py intake validate intake/incoming/<package-name>
```

#### 複数 HTML から選択

1 フォルダに複数 HTML がある場合、処理対象だけを選んで intake〜prepare まで実行できます。

```bash
# 一覧
python wpaipublish.py intake list <folder>

# 対話選択 → intake 作成
python wpaipublish.py intake select <folder> --interactive

# 指定ファイルで intake → validate → convert prepare
python wpaipublish.py intake pipeline <folder> \
  --select hero.html \
  --select pages/about.html \
  --target-type page
```

Web UI: `/pipeline`（ナビ「HTML選択」）でフォルダパス入力 → チェック選択 → パイプライン開始。  
サンプル: `intake/samples/multi-html/`

**完了条件**: `VALIDATION OK` が表示される（pipeline 利用時はセッションも作成済み）

### Phase 2: Claude Code による変換

**ポイント**: WordPress 向け変換そのものはコードを手書きせず、Claude Code への指示（`prompts/convert-to-wp.md` とセッションの `CLAUDE_INSTRUCTIONS.md`）だけで進められます。一方、intake・品質ゲート・デプロイなど一連のパイプラインは `wpaipublish.py` が必要で、Claude Code の設定だけでは完結しません。

最短フロー:

```text
CLI: convert prepare → Claude Code: 変換 → CLI: convert mark-done → quality / deploy
```

1. 変換セッション作成:

```bash
python wpaipublish.py convert prepare intake/incoming/<package-name>
```

2. 出力された `output/<session-id>/CLAUDE_INSTRUCTIONS.md` を確認
3. Claude Code で `prompts/convert-to-wp.md` に従い変換（PHP/ブロックを自分で書かなくてよい）
4. 変換結果を `output/<session-id>/wordpress/` に配置
5. `prompts/validate-theme.md` で自己検証
6. 変換完了:

```bash
python wpaipublish.py convert mark-done <session-id>
```

任意: Claude CLI 自動実行

```bash
python wpaipublish.py ai route --stage wp_conversion --session <session-id> --auto-cli
```

Agent 利用時: `wp_conversion` は手動ステージ。変換完了後に `python wpaipublish.py agent resume <session-id>`。

**完了条件**: `wordpress/` に必要ファイルが揃っている
### Phase 3: 自動検証

```bash
python wpaipublish.py validate run <session-id>
```

**確認項目**:
- PHP構文エラーなし
- 必須ファイル存在
- セキュリティ警告の確認

**完了条件**: `VALIDATION OK`

### Phase 4: デプロイ前レビュー

Claude Code で `prompts/deploy-review.md` に従いレビュー実施。

**完了条件**: 判定が `APPROVE`

### Phase 5: ステージングデプロイ

```bash
python wpaipublish.py deploy staging <session-id>
```

**確認項目**（ステージング環境で手動確認）:
- [ ] 対象ページ/ブロックの表示が正しい
- [ ] レスポンシブ表示（モバイル / タブレット / デスクトップ）
- [ ] JavaScript の動作（アニメーション、インタラクション）
- [ ] 既存ページへの影響がない
- [ ] コンソールエラーがない
- [ ] ページ読み込み速度に問題がない

### Phase 6: 本番デプロイ

ステージング確認完了後:

```bash
python wpaipublish.py deploy production <session-id> --confirm
```

**完了条件**: 本番サイトで表示・動作確認

### Phase 7: 後処理

```bash
# intake を processed に移動
mv intake/incoming/<package-name> intake/processed/

# セッション状態確認
python wpaipublish.py status
```

## 6. 定期運用

### 6.1 デプロイ履歴の確認

```bash
cat deployments/history.jsonl | python3 -m json.tool
```

### 6.2 古いセッションのクリーンアップ

30日以上前の `output/` セッションはアーカイブまたは削除:

```bash
find output/ -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;
```

### 6.3 バックアップの確認

本番デプロイ時に `deployments/backup-prod-*` が作成されることを確認。

## 7. トラブルシューティング

### intake バリデーション失敗

| エラー | 対処 |
|--------|------|
| manifest.json が見つからない | ファイル名・配置場所を確認 |
| ファイルが見つからない | `files[].path` と実ファイルの一致を確認 |
| version 不一致 | `"version": "1.0"` を設定 |

### REST API 接続エラー

```bash
# 接続テスト
curl -u "user:app-password" https://staging.example.com/wp-json/wp/v2/pages?per_page=1
```

- Application Password の再発行
- パーマリンク設定の再保存
- セキュリティプラグインの REST API 制限を確認

### WP-CLI / SSH エラー

```bash
ssh $WP_STAGING_SSH "cd $WP_STAGING_PATH && wp plugin list"
```

- SSH キーの権限（600）
- WordPress パスの確認
- WP-CLI のバージョン確認

### 変換結果の表示崩れ

1. ブラウザキャッシュをクリア
2. `wp cache flush` を実行
3. CSS の詳細度・セレクタ競合を確認
4. Claude Code で `prompts/validate-theme.md` に従い再修正

## 8. セキュリティガイドライン

1. `.env` は Git にコミットしない（`.gitignore` 済み）
2. Application Password はデプロイ専用ユーザーのみに付与
3. SSH キーはパスフレーズ付きを推奨
4. 本番デプロイは `--confirm` フラグ必須
5. AI生成コードは必ず検証パイプラインを通す

## 9. 変更管理

| 変更種別 | 承認 |
|----------|------|
| 新規ブロック追加 | 開発者 |
| 既存ブロック更新 | 開発者 + QA確認 |
| テーマ構造変更 | 開発者 + テックリード |
| 本番デプロイ | 開発者（ステージング確認済み） |

## 10. 連絡・エスカレーション

障害発生時:
1. ロールバック実行（`docs/ROLLBACK.md` 参照）
2. 影響範囲の確認
3. チームへの報告
4. 原因調査・再デプロイ計画
