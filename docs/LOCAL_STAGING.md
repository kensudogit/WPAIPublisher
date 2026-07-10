# ローカルステージング（Docker WordPress）

リモート WordPress がなくても、デモ〜ステージング反映までをローカルで完走できます。

## 前提

- Docker Desktop
- Python 3.10+
- Node.js（ビジュアル回帰用）

## 手順

```powershell
cd C:\devlop\WPAIPublisher

# 1. コンテナ起動
docker compose -f docker-compose.staging.yml up -d

# 2. WP インストール + テーマ有効化（Git Bash / WSL）
bash scripts/local/bootstrap_wp.sh

# 3. デモセッションをステージングへ反映
python wpaipublish.py deploy staging demo-20260709
```

## 確認

| URL | 内容 |
|-----|------|
| http://localhost:8088 | サイト |
| http://localhost:8088/wp-admin | 管理画面（`admin` / `admin1234`） |

ブロックはテーマ `custom-theme` の `blocks/hero-section` に配置されます。

SWELL パイプラインの場合は `swell-child` 子テーマとして配置されます。

```powershell
python wpaipublish.py deploy staging <swell-session>
# → staging/wp-content/themes/swell-child/
```

管理画面 → 外観 → テーマ で `swell-child` を有効化（親テーマ SWELL が必要）。詳細は [SWELL.md](SWELL.md#wordpress-への反映手順)。

固定ページで確認する場合:

1. 管理画面 → 固定ページ → 新規
2. ブロック挿入 → Hero Section
3. 公開

## 停止

```powershell
docker compose -f docker-compose.staging.yml down
```

データ保持のまま止める場合は `down`、完全削除は `down -v`。
