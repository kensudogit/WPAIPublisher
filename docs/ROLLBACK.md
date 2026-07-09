# WPAIPublisher ロールバック手順書

## 1. 概要

本番またはステージング環境へのデプロイ後に問題が発生した場合の復旧手順です。

## 2. ロールバックの種類

| 種類 | 対象 | 所要時間 | データ損失 |
|------|------|----------|-----------|
| 自動ロールバック | ファイルデプロイ（block/theme） | 5分以内 | なし |
| REST API ロールバック | 固定ページ（page） | 5分以内 | なし |
| Git ロールバック | Git管理下のテーマ | 10分以内 | なし |
| 手動ロールバック | 上記で対応不可の場合 | 30分以内 | 状況による |

## 3. ロールバック判断基準

以下のいずれかに該当する場合、ロールバックを実施:

- [ ] サイトが表示不能（500エラー、白画面）
- [ ] 重大な表示崩れ（レイアウト崩壊、コンテンツ欠落）
- [ ] JavaScript エラーによる機能停止
- [ ] セキュリティ脆弱性の発見
- [ ] 意図しない既存ページへの影響

**軽微な表示差異**（フォントサイズの微差等）はロールバックせず、修正デプロイで対応。

## 4. 自動ロールバック（推奨）

### 4.1 前提

- 本番デプロイ時に `deployments/backup-prod-*` が自動作成されている
- `deployments/history.jsonl` にデプロイ履歴が記録されている

### 4.2 手順

```bash
# 1. 影響を受けたセッションIDを特定
python wpaipublish.py status

# 2. ロールバック実行（本番）
python wpaipublish.py rollback <session-id> production --confirm

# 3. ステージングもロールバックする場合
python wpaipublish.py rollback <session-id> staging --confirm
```

### 4.3 確認

1. 本番サイトにアクセスし表示を確認
2. 影響を受けたページ/ブロックが復旧していることを確認
3. ブラウザキャッシュをクリアして再確認

```bash
# キャッシュクリア（サーバー側）
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp cache flush"
```

## 5. 手動ロールバック（ファイルデプロイ）

自動ロールバックが失敗した場合:

### 5.1 バックアップの確認

```bash
ls -lt deployments/backup-prod-*
ls -lt deployments/
```

最新のバックアップディレクトリを特定。

### 5.2 ファイル復元

```bash
# 変数設定
SESSION_ID="<session-id>"
BACKUP_DIR="deployments/backup-prod-YYYYMMDDHHMMSS"
THEME_SLUG="custom-theme"
BLOCK_NAME="hero-section"

# 本番へ復元
scp -r "$BACKUP_DIR/"* "$WP_PROD_SSH:$WP_PROD_PATH/wp-content/themes/$THEME_SLUG/blocks/$BLOCK_NAME/"

# キャッシュクリア
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp cache flush"
```

### 5.3 確認

本番サイトで表示・動作を確認。

## 6. REST API ロールバック（固定ページ）

### 6.1 ページのリビジョン復元

WordPress は固定ページのリビジョンを保持しています。

```bash
# ページIDを確認
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp post list --post_type=page --name=<page-slug> --format=ids"

# リビジョン一覧
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp post list --post_type=revision --post_parent=<page-id> --format=table"

# 直前のリビジョンに復元
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp post meta get <revision-id> _wp_old_slug"
```

### 6.2 WP-CLI でのコンテンツ復元

バックアップがある場合:

```bash
# デプロイ前にエクスポートしておいた場合
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp post update <page-id> --post_content='$(cat backup-content.html)'"
```

## 7. Git ロールバック

テーマが Git 管理されている場合:

```bash
# サーバー上で
ssh $WP_PROD_SSH "cd $WP_PROD_PATH/wp-content/themes/$THEME_SLUG && git log --oneline -5"

# 直前のコミットに戻す
ssh $WP_PROD_SSH "cd $WP_PROD_PATH/wp-content/themes/$THEME_SLUG && git checkout HEAD~1 -- ."

# キャッシュクリア
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp cache flush"
```

## 8. カスタムCSSのロールバック

```bash
# バックアップCSSがある場合
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp option patch update theme_mods_$THEME_SLUG custom_css '$(cat backup.css)'"
```

## 9. ロールバック後の対応

### 9.1 記録

ロールバック実施後、以下を記録:

- 実施日時
- 対象セッションID
- ロールバック方法（自動 / 手動）
- 復元元バックアップ
- 障害の概要
- 根本原因（判明している場合）

### 9.2 再デプロイ計画

1. `output/<session-id>/` の変換結果を修正
2. `prompts/validate-theme.md` で再検証
3. ステージングで再確認
4. 本番へ再デプロイ

### 9.3 予防策

| 問題 | 予防策 |
|------|--------|
| バックアップ不在 | 本番デプロイ前にバックアップ存在を確認 |
| 表示崩れ見逃し | ステージング確認チェックリストを厳守 |
| 既存機能への影響 | デプロイ前レビューで影響範囲を確認 |
| セキュリティ問題 | 自動検証のセキュリティチェックを必ず実行 |

## 10. 緊急連絡フロー

```
障害検知
  ↓
ロールバック実施（本手順書）
  ↓
サイト復旧確認
  ↓
チーム報告
  ↓
原因調査
  ↓
修正・再デプロイ計画
```

## 11. バックアップ戦略（推奨）

### デプロイ前（自動）

- `deploy_production.sh` が `deployments/backup-prod-*` を自動作成

### 定期バックアップ（手動設定推奨）

```bash
# 日次テーマバックアップ（cron）
0 3 * * * tar czf /backup/theme-$(date +\%Y\%m\%d).tar.gz /var/www/production/wp-content/themes/custom-theme
```

### データベース

ファイルロールバックでは DB は変更されませんが、ページコンテンツの REST API 更新時はリビジョンが作成されます。重要な更新前は DB バックアップも推奨:

```bash
ssh $WP_PROD_SSH "cd $WP_PROD_PATH && wp db export /backup/db-$(date +%Y%m%d).sql"
```
