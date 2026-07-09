# Claude Code プロンプト: AI出力 → WordPress 変換

あなたは WordPress 開発の専門家です。AIコーディングツール（Codex等）が生成した HTML / CSS / JavaScript を、WordPress のベストプラクティスに従って変換してください。

## 入力

- `source/` ディレクトリ内のファイル（HTML, CSS, JS）
- `task.json` 内のマニフェスト（`target.type` で変換先を判定）

## 出力先

`wordpress/` ディレクトリに変換結果を出力してください。

---

## 変換ルール（共通）

### セキュリティ
- `eval()`, `exec()`, `innerHTML` への未サニタイズ代入は禁止
- ユーザー入力を直接出力しない（`esc_html()`, `esc_attr()`, `esc_url()` を使用）
- 外部スクリプトの読み込みは `wp_enqueue_script()` 経由

### アクセシビリティ
- セマンティックHTML（`header`, `main`, `section`, `nav` 等）を維持
- 画像に `alt` 属性、インタラクティブ要素にキーボード操作を確保
- カラーコントラスト比 WCAG AA 準拠を意識

### パフォーマンス
- CSS/JS は可能な限り1ファイルにまとめ、WordPress の enqueue で読み込む
- インラインスタイル・スクリプトは最小限に
- 画像は `wp_get_attachment_image()` または lazy loading 対応

### 命名規則
- PHP関数名: `theme_slug_` プレフィックス（例: `mytheme_render_hero`）
- CSSクラス: BEM記法を維持（元の命名を尊重）
- ファイル名: ケバブケース（例: `hero-section.php`）

---

## target.type 別の変換手順

### `block`（Gutenberg カスタムブロック）

以下のファイル構成で出力:

```
wordpress/
├── block.json          # ブロック定義（API v3）
├── index.php           # ブロック登録・レンダリング
├── render.php          # サーバーサイドレンダリング
├── style.css           # フロントエンドスタイル
├── editor.css          # エディタ用スタイル（任意）
└── view.js             # フロントエンドJS（任意）
```

**block.json テンプレート:**
```json
{
  "$schema": "https://schemas.wp.org/trunk/block.json",
  "apiVersion": 3,
  "name": "theme-slug/block-name",
  "title": "ブロック表示名",
  "category": "theme",
  "icon": "star-filled",
  "supports": { "html": false, "align": ["wide", "full"] },
  "textdomain": "theme-slug",
  "editorScript": "file:./index.js",
  "style": "file:./style.css",
  "render": "file:./render.php"
}
```

**render.php テンプレート:**
```php
<?php
/**
 * @var array    $attributes ブロック属性
 * @var string   $content    ブロックコンテンツ
 * @var WP_Block $block      ブロックインスタンス
 */
?>
<section <?php echo get_block_wrapper_attributes(); ?>>
  <!-- HTMLをPHPテンプレートに変換。動的値は esc_html() 等でエスケープ -->
</section>
```

### `theme`（テーマファイル）

```
wordpress/
├── style.css           # テーマヘッダー必須
├── functions.php       # enqueue, ブロック登録
├── index.php
├── front-page.php      # 必要に応じて
├── assets/
│   ├── css/
│   └── js/
└── parts/              # テンプレートパーツ
```

**style.css ヘッダー必須:**
```css
/*
Theme Name: Custom Theme
Description: AI-generated theme
Version: 1.0.0
Requires at least: 6.0
*/
```

### `page`（固定ページコンテンツ）

```
wordpress/
└── content.html        # ブロックエディタ互換HTML
```

- Gutenberg ブロックコメント形式（`<!-- wp:group -->` 等）に変換
- カスタムHTMLブロックは最終手段として使用

### `template-part`

```
wordpress/
└── parts/
    └── part-name.html  # フルサイト編集用テンプレートパーツ
```

### `custom-css`

```
wordpress/
└── custom.css          # 追加CSSとしてそのまま使用可能な形式
```

---

## 変換チェックリスト

変換完了前に以下を確認:

- [ ] 全PHPファイルに `<?php` タグと適切なファイルヘッダーコメント
- [ ] ハードコードされたURLを `home_url()` / `get_template_directory_uri()` に置換
- [ ] 画像パスをメディアライブラリ参照またはテーマアセットパスに変換
- [ ] CSSの `!important` 乱用を避け、WordPress固有のセレクタ競合を考慮
- [ ] JSは IIFE または ES module でラップし、グローバル汚染を防止
- [ ] `textdomain` をマニフェストの `theme_slug` と一致させる

## 完了後

1. `prompts/validate-theme.md` に従い自己検証
2. 問題があれば修正
3. 以下を実行:
   ```
   python wpaipublish.py convert mark-done <session_id>
   ```
