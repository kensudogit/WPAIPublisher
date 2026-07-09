#!/usr/bin/env python3
"""複数HTMLが含まれるフォルダから処理対象を選択し、intake パッケージを作成する"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.config import get_intake_dir  # noqa: E402

ASSET_EXTS = {".css": "css", ".js": "js", ".mjs": "js", ".png": "asset", ".jpg": "asset",
              ".jpeg": "asset", ".webp": "asset", ".svg": "asset", ".gif": "asset"}


def slugify(name: str) -> str:
    base = Path(name).stem
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-").lower()
    return slug or "page"


def list_html_files(source_dir: Path) -> list[dict]:
    source_dir = source_dir.resolve()
    files = []
    for path in sorted(source_dir.rglob("*.html")):
        if path.name.startswith("."):
            continue
        rel = path.relative_to(source_dir).as_posix()
        companions = find_companions(source_dir, path)
        files.append({
            "path": rel,
            "name": path.name,
            "size": path.stat().st_size,
            "companions": [c.relative_to(source_dir).as_posix() for c in companions],
        })
    return files


def find_companions(source_dir: Path, html_path: Path) -> list[Path]:
    """同名の css/js と、HTML 内で相対参照されているローカル資産を収集"""
    source_dir = source_dir.resolve()
    html_path = html_path.resolve()
    found: list[Path] = []
    stem = html_path.stem
    parent = html_path.parent

    for ext in (".css", ".js", ".mjs"):
        candidate = parent / f"{stem}{ext}"
        if candidate.exists() and candidate.is_file():
            found.append(candidate.resolve())

    try:
        text = html_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return found

    refs = re.findall(
        r"""(?:href|src)\s*=\s*["']([^"']+\.(?:css|js|mjs|png|jpe?g|webp|svg|gif))["']""",
        text,
        flags=re.I,
    )
    for ref in refs:
        if ref.startswith(("http://", "https://", "//", "data:")):
            continue
        ref_path = (html_path.parent / ref).resolve()
        try:
            ref_path.relative_to(source_dir)
        except ValueError:
            continue
        if ref_path.exists() and ref_path.is_file() and ref_path not in found:
            found.append(ref_path)
    return found


def build_manifest(
    selected: list[Path],
    source_dir: Path,
    *,
    package_name: str,
    target_type: str,
    theme_slug: str,
    tool: str,
    notes: str,
) -> dict:
    files = []
    for html in selected:
        rel = html.relative_to(source_dir).as_posix()
        files.append({
            "path": Path(rel).name if "/" not in rel else rel.replace("/", "__"),
            "role": "html",
            "description": f"Selected from {rel}",
            "source": rel,
        })
        for companion in find_companions(source_dir, html):
            crel = companion.relative_to(source_dir).as_posix()
            dest_name = Path(crel).name if "/" not in crel else crel.replace("/", "__")
            role = ASSET_EXTS.get(companion.suffix.lower(), "other")
            files.append({
                "path": dest_name,
                "role": role,
                "description": f"Companion of {rel}",
                "source": crel,
            })

    # de-dupe by dest path
    seen = set()
    unique_files = []
    for f in files:
        if f["path"] in seen:
            continue
        seen.add(f["path"])
        unique_files.append(f)

    primary = selected[0]
    block_name = slugify(primary.name)
    page_slug = block_name

    target: dict = {"type": target_type, "theme_slug": theme_slug}
    if target_type == "block":
        target["block_name"] = block_name
    elif target_type == "page":
        target["page_slug"] = page_slug

    return {
        "version": "1.0",
        "source": {
            "tool": tool,
            "prompt": f"Selected {len(selected)} HTML file(s) from {source_dir}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "target": target,
        "files": [{"path": f["path"], "role": f["role"], "description": f["description"]} for f in unique_files],
        "notes": notes or f"Selected files: {', '.join(p.name for p in selected)}",
        "_copy_map": {f["path"]: f["source"] for f in unique_files},
    }


def create_package(
    source_dir: Path,
    selected_rels: list[str],
    *,
    package_name: str | None = None,
    target_type: str = "page",
    theme_slug: str = "custom-theme",
    tool: str = "other",
    notes: str = "",
) -> Path:
    source_dir = source_dir.resolve()
    if not source_dir.is_dir():
        raise FileNotFoundError(f"ソースフォルダがありません: {source_dir}")

    selected: list[Path] = []
    for rel in selected_rels:
        path = (source_dir / rel).resolve()
        try:
            path.relative_to(source_dir)
        except ValueError as e:
            raise ValueError(f"フォルダ外のファイルは指定できません: {rel}") from e
        if not path.exists() or path.suffix.lower() != ".html":
            raise FileNotFoundError(f"HTMLファイルが見つかりません: {rel}")
        selected.append(path)

    if not selected:
        raise ValueError("HTMLファイルが選択されていません")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    pkg = package_name or f"selected-{slugify(selected[0].name)}-{stamp}"
    dest = get_intake_dir() / "incoming" / pkg
    if dest.exists():
        raise FileExistsError(f"パッケージが既に存在します: {dest}")
    dest.mkdir(parents=True)

    manifest = build_manifest(
        selected,
        source_dir,
        package_name=pkg,
        target_type=target_type,
        theme_slug=theme_slug,
        tool=tool,
        notes=notes,
    )
    copy_map = manifest.pop("_copy_map")
    for dest_name, src_rel in copy_map.items():
        src = source_dir / src_rel
        shutil.copy2(src, dest / dest_name)

    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (dest / "selection.json").write_text(
        json.dumps(
            {
                "source_dir": str(source_dir),
                "selected": selected_rels,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="複数HTMLから処理対象を選択して intake を作成")
    sub = parser.add_subparsers(dest="action", required=True)

    p_list = sub.add_parser("list", help="フォルダ内の HTML 一覧")
    p_list.add_argument("source_dir", help="HTML が含まれるフォルダ")
    p_list.add_argument("--json", action="store_true")

    p_create = sub.add_parser("create", help="選択した HTML で intake パッケージ作成")
    p_create.add_argument("source_dir", help="HTML が含まれるフォルダ")
    p_create.add_argument(
        "--select",
        action="append",
        required=True,
        help="選択する HTML の相対パス（複数可）",
    )
    p_create.add_argument("--package-name", help="intake パッケージ名")
    p_create.add_argument("--target-type", default="page", choices=["page", "block", "theme", "template-part", "custom-css"])
    p_create.add_argument("--theme-slug", default="custom-theme")
    p_create.add_argument("--tool", default="other", choices=["codex", "cursor", "copilot", "other"])
    p_create.add_argument("--notes", default="")
    p_create.add_argument("--json", action="store_true")

    p_interactive = sub.add_parser("interactive", help="対話的に HTML を選択")
    p_interactive.add_argument("source_dir")
    p_interactive.add_argument("--target-type", default="page", choices=["page", "block", "theme", "template-part", "custom-css"])
    p_interactive.add_argument("--theme-slug", default="custom-theme")
    p_interactive.add_argument("--tool", default="other")

    args = parser.parse_args()
    source_dir = Path(args.source_dir)

    if args.action == "list":
        files = list_html_files(source_dir)
        if args.json:
            print(json.dumps({"source_dir": str(source_dir), "files": files}, indent=2, ensure_ascii=False))
        else:
            if not files:
                print("HTMLファイルがありません")
                return 1
            print(f"{'#':<4} {'Path':<50} {'Size':>8}  Companions")
            print("-" * 90)
            for i, f in enumerate(files, 1):
                comps = ", ".join(Path(c).name for c in f["companions"]) or "-"
                print(f"{i:<4} {f['path']:<50} {f['size']:>8}  {comps}")
        return 0

    if args.action == "interactive":
        files = list_html_files(source_dir)
        if not files:
            print("HTMLファイルがありません", file=sys.stderr)
            return 1
        print("処理対象の HTML を選んでください（番号をカンマ区切り、例: 1,3）\n")
        for i, f in enumerate(files, 1):
            comps = ", ".join(Path(c).name for c in f["companions"]) or "-"
            print(f"  [{i}] {f['path']}  (+ {comps})")
        raw = input("\n番号: ").strip()
        if not raw:
            print("未選択", file=sys.stderr)
            return 1
        indexes = []
        for part in raw.split(","):
            part = part.strip()
            if not part.isdigit():
                print(f"不正な番号: {part}", file=sys.stderr)
                return 1
            indexes.append(int(part))
        selected = []
        for idx in indexes:
            if idx < 1 or idx > len(files):
                print(f"範囲外: {idx}", file=sys.stderr)
                return 1
            selected.append(files[idx - 1]["path"])
        dest = create_package(
            source_dir,
            selected,
            target_type=args.target_type,
            theme_slug=args.theme_slug,
            tool=args.tool,
        )
        print(f"Created: {dest}")
        print("Next: python wpaipublish.py intake validate " + str(dest))
        return 0

    # create
    dest = create_package(
        source_dir,
        args.select,
        package_name=args.package_name,
        target_type=args.target_type,
        theme_slug=args.theme_slug,
        tool=args.tool,
        notes=args.notes,
    )
    if args.json:
        print(json.dumps({"package": str(dest), "manifest": str(dest / "manifest.json")}, indent=2))
    else:
        print(f"Created: {dest}")
        print(f"Files: {len(list(dest.iterdir()))}")
        print("Next: python wpaipublish.py intake validate " + str(dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
