# SWELL パイプライン

AI 生成 HTML を SWELL 子テーマ構成へ変換し、デプロイ・表示確認・レポートまで自動化します。

## フロー

```text
HTML フォルダ
  → analyze（structure.json: 構造・コンポーネント・振り分け）
  → swell convert（子テーマ / blocks / template-parts / templates）
  → validate
  → deploy staging（ローカル Docker または staging/）
  → visual（Playwright ピクセル差分）
  → git commit/push（任意）
  → report（change_report.md / .json）
```

## 振り分けルール

| 検出 | 出力先 |
|------|--------|
| hero / cta / card / faq / gallery 等 | `blocks/<name>/`（block.json + render.php） |
| header / nav / footer | `template-parts/<name>.php` |
| ページ本体 | `templates/page-<slug>.html` + `content.html` |
| CSS/JS | `assets/css|js/wpaipublisher.css|js` |
| 子テーマ本体 | `style.css`（`Template: swell`）+ `functions.php` |

## コマンド

```bash
python wpaipublish.py swell pipeline <session> \
  --source-dir <folder> --select a.html \
  --visual-update

python wpaipublish.py analyze <session>
python wpaipublish.py swell convert <session>
python wpaipublish.py deploy staging <session>
python wpaipublish.py visual run <session> --update
python wpaipublish.py git commit <session> --push
python wpaipublish.py report generate <session>
```

## Web

`/swell` からパイプライン実行と変更レポート確認が可能です（既定では Git push はしません）。

Railway 上の実行は変換・検証・レポートまで可能ですが、**あなたの WordPress サーバーへは自動では届きません**。WP 反映は下の手順でローカル CLI または手動コピーを行ってください。

## WordPress への反映手順

成果物の本体は次です。

```text
output/<session>/wordpress/
  style.css          # Template: swell（子テーマヘッダー）
  functions.php
  blocks/            # カスタムブロック
  template-parts/    # ヘッダー等
  templates/         # ページテンプレート
  content.html       # ページ本文の参考 HTML
  assets/            # CSS / JS
```

前提: 反映先 WP に **親テーマ SWELL** がインストール済みであること。

### A. ローカル Docker staging（最短・推奨）

1. Docker WP を起動し、初回だけブートストラップします。

```bash
docker compose -f docker-compose.staging.yml up -d
bash scripts/local/bootstrap_wp.sh
```

2. SWELL パイプラインを実行します（`deploy_staging` まで含む）。

```bash
python wpaipublish.py swell pipeline swell-demo \
  --source-dir intake/samples/multi-html \
  --select "**/*.html" \
  --visual-update
```

または、既にセッションがある場合:

```bash
python wpaipublish.py deploy staging <session>
```

3. 配置先と確認 URL

| 項目 | 内容 |
|------|------|
| 配置先 | `staging/wp-content/themes/swell-child/`（`WP_STAGING_LOCAL_PATH` で変更可） |
| サイト | http://localhost:8088 |
| 管理画面 | http://localhost:8088/wp-admin （`admin` / `admin1234`） |

4. 管理画面 → **外観 → テーマ** で `swell-child` が有効か確認（Docker 起動時は WP-CLI で自動有効化を試行します）。
5. 固定ページを新規作成し、必要ならブロック挿入や `content.html` の内容を貼り付けて表示確認します。

詳細: [LOCAL_STAGING.md](LOCAL_STAGING.md)

### B. 既存の SWELL サイトへ手動反映

1. `output/<session>/wordpress/` を ZIP にするか、フォルダごとコピーします。
2. サーバーの `wp-content/themes/swell-child/` に配置（既存があればバックアップ後に上書き）。
3. WP 管理画面 → **外観 → テーマ** → 子テーマを有効化。
4. **設定 → パーマリンク** を「変更を保存」で再保存（必要に応じて）。
5. キャッシュプラグイン / CDN / SWELL キャッシュをクリア。
6. 固定ページやテンプレートでブロック・表示を確認します。

### C. リモート staging / 本番（SSH + WP-CLI）

1. `config/.env` を設定します。

| 変数 | 用途 |
|------|------|
| `WP_STAGING_SSH` / `WP_STAGING_PATH` | ステージング SSH と WP ルート |
| `WP_STAGING_URL` | 確認用 URL |
| `WP_PROD_SSH` / `WP_PROD_PATH` | 本番（同様） |

2. 検証済みセッションをデプロイします。

```bash
# ステージング（ローカル配置 + SSH 設定時は scp）
python wpaipublish.py deploy staging <session>

# 本番（承認必須）
python wpaipublish.py deploy production <session> --confirm
```

3. リモートでテーマ有効化（例）:

```bash
ssh $WP_STAGING_SSH "cd $WP_STAGING_PATH && wp theme activate swell-child && wp cache flush"
```

4. ステージングで表示確認後に本番へ進みます。障害時は [ROLLBACK.md](ROLLBACK.md)。

### D. Web（`/swell`）実行後の流れ

1. `/swell` でサンプル実行または HTML アップロード → セッション ID とレポートを確認。
2. 成果物はサーバー上の `output/<session>/wordpress/` にあります（Railway ではコンテナ内）。
3. **WP 本体への反映はローカルで** `deploy staging <session>` を実行するか、上記 B の手動コピーを行います。
4. ローカルに成果物が無い場合は、同じ HTML で CLI の `swell pipeline` を再実行するのが確実です。

### 確認チェックリスト

- [ ] 親テーマ SWELL が有効（またはインストール済み）
- [ ] 子テーマ `swell-child`（または指定 slug）が有効
- [ ] `blocks/` のブロックがエディタに出る
- [ ] CSS/JS（`assets/`）が読み込まれている
- [ ] モバイル表示・コンソールエラーなし
- [ ] `change_report.md` の内容と画面が一致
