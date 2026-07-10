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
