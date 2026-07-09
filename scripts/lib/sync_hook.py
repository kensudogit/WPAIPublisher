#!/usr/bin/env python3
"""セッション状態を PostgreSQL へベストエフォート同期"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def sync_session(session_id: str) -> None:
    try:
        from lib.session_store import database_url, upsert_from_task_file
        from lib.config import get_output_dir

        if not database_url():
            return
        session_dir = get_output_dir() / session_id
        if upsert_from_task_file(session_dir):
            print(f"[db] synced session: {session_id}")
    except Exception as e:  # noqa: BLE001 — never block pipeline
        print(f"[db] sync skipped: {e}", file=sys.stderr)
