#!/usr/bin/env python3
"""セッションを PostgreSQL に永続化する"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _load_env() -> dict[str, str]:
    env_path = ROOT / "config" / ".env"
    result: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip().strip('"').strip("'")
    return {**result, **os.environ}


def database_url() -> str:
    env = _load_env()
    return env.get("DATABASE_URL", "").strip()


def _connect():
    url = database_url()
    if not url:
        return None
    try:
        import psycopg
    except ImportError as e:
        raise RuntimeError("psycopg が未インストールです: pip install 'psycopg[binary]'") from e
    return psycopg.connect(url)


def ensure_schema() -> bool:
    conn = _connect()
    if conn is None:
        return False
    schema = (ROOT / "scripts" / "db" / "schema.sql").read_text(encoding="utf-8")
    with conn:
        with conn.cursor() as cur:
            cur.execute(schema)
    conn.close()
    return True


def upsert_session(
    session_id: str,
    *,
    status: str = "unknown",
    agent: str = "-",
    target: str = "?",
    staging_url: str | None = None,
    production_url: str | None = None,
    notes: str | None = None,
    manifest: dict[str, Any] | None = None,
    task: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> bool:
    conn = _connect()
    if conn is None:
        return False
    ensure_schema()
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (
                  id, status, agent, target, staging_url, production_url,
                  notes, manifest, task, created_at, updated_at
                ) VALUES (
                  %(id)s, %(status)s, %(agent)s, %(target)s, %(staging_url)s, %(production_url)s,
                  %(notes)s, %(manifest)s::jsonb, %(task)s::jsonb, COALESCE(%(created_at)s::timestamptz, NOW()), NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                  status = EXCLUDED.status,
                  agent = EXCLUDED.agent,
                  target = EXCLUDED.target,
                  staging_url = COALESCE(EXCLUDED.staging_url, sessions.staging_url),
                  production_url = COALESCE(EXCLUDED.production_url, sessions.production_url),
                  notes = COALESCE(EXCLUDED.notes, sessions.notes),
                  manifest = COALESCE(EXCLUDED.manifest, sessions.manifest),
                  task = COALESCE(EXCLUDED.task, sessions.task),
                  updated_at = NOW()
                """,
                {
                    "id": session_id,
                    "status": status,
                    "agent": agent or "-",
                    "target": target or "?",
                    "staging_url": staging_url,
                    "production_url": production_url,
                    "notes": notes,
                    "manifest": json.dumps(manifest, ensure_ascii=False) if manifest is not None else None,
                    "task": json.dumps(task, ensure_ascii=False) if task is not None else None,
                    "created_at": created_at,
                },
            )
    conn.close()
    return True


def upsert_from_task_file(session_dir: Path) -> bool:
    task_path = session_dir / "task.json"
    if not task_path.exists():
        return False
    task = json.loads(task_path.read_text(encoding="utf-8"))
    session_id = task.get("session_id") or session_dir.name
    agent = "-"
    agent_path = session_dir / "agent_state.json"
    if agent_path.exists():
        try:
            agent = json.loads(agent_path.read_text(encoding="utf-8")).get("status", "-") or "-"
        except json.JSONDecodeError:
            pass
    manifest = task.get("manifest") or {}
    target = (manifest.get("target") or {}).get("type", "?")
    return upsert_session(
        session_id,
        status=task.get("status", "unknown"),
        agent=agent,
        target=target,
        staging_url=task.get("staging_url"),
        production_url=task.get("production_url"),
        notes=task.get("notes"),
        manifest=manifest,
        task=task,
        created_at=task.get("created_at"),
    )


def sync_all_sessions(output_dir: Path | None = None) -> list[str]:
    output_dir = output_dir or (ROOT / "output")
    synced: list[str] = []
    if not output_dir.exists():
        return synced
    if not database_url():
        return synced
    ensure_schema()
    for path in sorted(output_dir.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        if upsert_from_task_file(path):
            synced.append(path.name)
    return synced


def list_sessions(limit: int = 100) -> list[dict[str, Any]]:
    conn = _connect()
    if conn is None:
        return []
    ensure_schema()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, status, agent, target, staging_url, production_url, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "status": r[1],
            "agent": r[2],
            "target": r[3],
            "staging_url": r[4],
            "production_url": r[5],
            "updated_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]
