# Claude Code プロンプト: 新規 intake パッケージ作成支援

Codex 等の AI ツールから出力された HTML/CSS/JS を、WPAIPublisher の intake 形式に整えるためのプロンプトです。

## タスク

以下の AI 生成ファイルを、WPAIPublisher の intake パッケージ形式に整形してください。

## 出力形式

`intake/incoming/<package-name>/` ディレクトリを作成し、以下を配置:

```
intake/incoming/<package-name>/
├── manifest.json       # 必須: マニフェスト
├── *.html              # HTMLファイル
├── *.css               # CSSファイル
└── *.js                # JavaScriptファイル
```

## manifest.json の作成ルール

`intake/manifest.schema.json` に準拠すること。

必須フィールド:
- `version`: `"1.0"`
- `source.tool`: 生成元（`codex`, `cursor`, `copilot`, `other`）
- `source.generated_at`: ISO 8601 形式の日時
- `target.type`: `block` | `theme` | `page` | `template-part` | `custom-css`
- `target.theme_slug`: 対象テーマのスラッグ
- `files`: ファイル一覧（`path`, `role` 必須）

### role の値
| 拡張子 | role |
|--------|------|
| .html  | html |
| .css   | css  |
| .js    | js   |
| .php   | php  |
| .json  | json |
| 画像等 | asset |

## 整形時の注意

1. HTMLからインラインCSS/JSを分離（可能な場合）
2. 外部CDNリンクは `notes` に記載
3. 画像はローカルファイルとして同梱するか、`notes` にメディアライブラリIDを記載
4. パッケージ名はケバブケース（例: `hero-section-20260709`）

## 完了後

バリデーションを実行:
```
python wpaipublish.py intake validate intake/incoming/<package-name>
```

成功したら変換準備:
```
python wpaipublish.py convert prepare intake/incoming/<package-name>
```
