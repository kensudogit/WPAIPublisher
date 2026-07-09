# Claude Code プロンプト: デプロイ前レビュー

ステージング環境へのデプロイ前に、最終レビューを実施してください。

## レビュー対象

- `output/<session_id>/wordpress/` の全ファイル
- `output/<session_id>/task.json` のマニフェスト
- `output/<session_id>/validation.json` の自動検証結果

## レビュー観点

### ビジネス要件
- マニフェストの `notes` に記載された要件を満たしているか
- 元の `source/` ファイルのデザイン・機能が再現されているか

### デプロイ安全性
- 本番環境の既存テーマ/ブロックを破壊しないか
- データベース変更を伴わないか（ファイルデプロイのみであること）
- ロールバック可能な変更であるか

### 影響範囲
- 変更が対象ブロック/ページのみに限定されているか
- グローバルな `functions.php` 変更がある場合、副作用はないか

## 出力形式

レビュー結果を `output/<session_id>/deploy-review.md` に記載:

```markdown
# デプロイ前レビュー

## 判定: APPROVE / NEEDS_CHANGES / REJECT

## 確認事項
- [ ] 要件充足
- [ ] セキュリティ
- [ ] 既存機能への影響なし
- [ ] ロールバック可能

## 指摘事項
（あれば記載）

## 推奨デプロイ手順
1. ステージングデプロイ
2. 確認項目: ...
3. 本番デプロイ
```

## 判定後のアクション

- **APPROVE**: ステージングデプロイを実行
  ```
  python wpaipublish.py deploy staging <session_id>
  ```
- **NEEDS_CHANGES**: 指摘事項を修正後、再レビュー
- **REJECT**: 変換からやり直し
