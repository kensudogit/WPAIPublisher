# PostgreSQL セッション永続化

Railway の Postgres サービスにセッション状態を保存し、ダッシュボードから参照します。

## 1. Railway 設定

1. プロジェクトに **Postgres** があることを確認（画像では Online）
2. **WPAIPublisher** サービス → Variables
3. `DATABASE_URL` を追加 → **Add Reference** → Postgres → `DATABASE_URL`
4. Redeploy

## 2. ローカルから同期

```powershell
cd C:\devlop\WPAIPublisher
pip install -r requirements.txt

# config/.env に Railway の DATABASE_URL を設定（Public URL 可）
# DATABASE_URL=postgresql://...

python wpaipublish.py db sync
python wpaipublish.py db list
```

## 3. 自動同期タイミング

以下の操作後に `task.json` が更新され、`DATABASE_URL` があれば自動 upsert されます。

- `convert prepare`
- `convert mark-done`
- `validate run`
- `deploy staging`

## 4. スキーマ

`scripts/db/schema.sql` の `sessions` テーブル。初回接続時に自動作成されます。

## 5. API

Web の `/api/sessions` は:

1. `DATABASE_URL` があれば PostgreSQL から取得
2. なければローカル `output/` にフォールバック
