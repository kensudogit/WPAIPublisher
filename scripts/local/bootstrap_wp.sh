#!/usr/bin/env bash
# Docker WordPress をインストールし、テーマを有効化
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[local] Waiting for WordPress..."
for i in $(seq 1 60); do
  if curl -fsS "http://localhost:8088" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

docker compose -f docker-compose.staging.yml exec -T wpcli \
  wp core is-installed --allow-root 2>/dev/null || \
docker compose -f docker-compose.staging.yml exec -T wpcli \
  wp core install \
    --url="http://localhost:8088" \
    --title="WPAIPublisher Staging" \
    --admin_user="admin" \
    --admin_password="admin1234" \
    --admin_email="admin@example.com" \
    --skip-email \
    --allow-root

docker compose -f docker-compose.staging.yml exec -T wpcli \
  wp theme activate custom-theme --allow-root

docker compose -f docker-compose.staging.yml exec -T wpcli \
  wp rewrite structure '/%postname%/' --allow-root

docker compose -f docker-compose.staging.yml exec -T wpcli \
  wp rewrite flush --hard --allow-root

# Application Password for REST API (best-effort; may need WP 5.6+)
docker compose -f docker-compose.staging.yml exec -T wpcli \
  wp user application-password create admin wpai-deploy --porcelain --allow-root \
  > "$ROOT_DIR/staging/app-password.txt" 2>/dev/null || true

echo "[local] WordPress ready: http://localhost:8088"
echo "[local] Admin: admin / admin1234"
if [[ -f "$ROOT_DIR/staging/app-password.txt" ]]; then
  echo "[local] App password saved: staging/app-password.txt"
fi
