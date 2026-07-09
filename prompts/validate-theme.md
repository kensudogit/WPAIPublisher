# Claude Code プロンプト: WordPress 変換結果の検証

変換済みの `wordpress/` ディレクトリを検証し、問題があれば修正してください。

## 検証項目

### 1. ファイル構成
- `task.json` の `target.type` に必要なファイルが揃っているか
- 不要なファイル（`.DS_Store`, `Thumbs.db` 等）が含まれていないか

### 2. PHP 品質
- 全 `.php` ファイルの構文が正しいか
- WordPress コーディング規約に準拠しているか
- 直接アクセス防止: `defined('ABSPATH') || exit;` がエントリーポイントにあるか
- エスケープ関数が適切に使用されているか

### 3. ブロック（type=block の場合）
- `block.json` が WordPress Block API v3 スキーマに準拠
- `name` が `theme-slug/block-name` 形式
- `render.php` が存在し、`get_block_wrapper_attributes()` を使用
- `block.json` の `name` と PHP内の登録名が一致

### 4. セキュリティ
以下のパターンがないことを確認:
- `eval(`, `exec(`, `system(`, `shell_exec(`
- `$_GET`, `$_POST` の未サニタイズ出力
- `innerHTML =` への未エスケープ代入（JS）

### 5. WordPress 互換性
- `wp_enqueue_style()` / `wp_enqueue_script()` でアセット登録
- ハードコードURLがない（`http://`, `https://` の直書き）
- テーマ/プラグインのプレフィックスが一貫している

### 6. レスポンシブ・アクセシビリティ
- `clamp()`, `min()`, `max()` またはメディアクエリでレスポンシブ対応
- フォーカス可能要素に `:focus-visible` スタイル
- 装飾的画像以外に `alt` 属性

## 修正方針

問題を発見した場合:
1. 問題の深刻度を判定（ERROR / WARNING）
2. ERROR は必ず修正してから完了
3. WARNING は `task.json` の notes に記録

## 検証完了後

修正が完了したら:
```
python wpaipublish.py convert mark-done <session_id> --notes "検証完了。WARNING: ..."
```

その後、自動検証を実行:
```
python wpaipublish.py validate run <session_id>
```
