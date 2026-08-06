#!/usr/bin/env python3
"""Download curated Sketchfab models using the authenticated Download API."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import requests

API_ROOT = "https://api.sketchfab.com/v3"
CHUNK_SIZE = 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--token", default=os.environ.get("SKETCHFAB_TOKEN"))
    parser.add_argument(
        "--auth-scheme",
        choices=("Token", "Bearer"),
        default=os.environ.get("SKETCHFAB_AUTH_SCHEME", "Token"),
        help="Use Token for a Sketchfab API token or Bearer for an OAuth access token.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--category", action="append", default=[])
    return parser.parse_args()


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"Unsafe archive member: {member.filename}")
    archive.extractall(destination)


def request_download_metadata(
    session: requests.Session, uid: str
) -> dict[str, Any]:
    response = session.get(f"{API_ROOT}/models/{uid}/download", timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected download response for {uid}")
    return payload


def choose_package(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for key in ("gltf", "glb"):
        item = payload.get(key)
        if isinstance(item, dict) and item.get("url"):
            return key, item
    available = ", ".join(sorted(payload)) or "none"
    raise ValueError(f"No glTF/GLB package returned. Available keys: {available}")


def download_file(
    session: requests.Session, url: str, destination: Path
) -> None:
    with session.get(url, stream=True, timeout=(30, 300)) as response:
        response.raise_for_status()
        with destination.open("wb") as stream:
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk:
                    stream.write(chunk)


def find_scene_file(folder: Path) -> Path:
    candidates = sorted(folder.rglob("*.glb"))
    if not candidates:
        candidates = sorted(folder.rglob("*.gltf"))
    if not candidates:
        raise FileNotFoundError(f"No .glb or .gltf found under {folder}")
    preferred = [p for p in candidates if p.name.lower() in {"scene.glb", "scene.gltf"}]
    return preferred[0] if preferred else candidates[0]


def write_attribution(category_root: Path, row: dict[str, str]) -> None:
    text = (
        f"# Source attribution\n\n"
        f"- Object: {row['object_name']}\n"
        f"- Author: {row['author']}\n"
        f"- Sketchfab model: {row['model_url']}\n"
        f"- License listed in catalog: {row['license']}\n"
        f"- Sketchfab UID: `{row['sketchfab_uid']}`\n\n"
        "Verify the source page and license before redistribution.\n"
    )
    (category_root / "ATTRIBUTION.md").write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    if not args.token:
        print(
            "Missing Sketchfab token. Set SKETCHFAB_TOKEN or pass --token.",
            file=sys.stderr,
        )
        return 2

    repo_root = args.repo_root.resolve()
    catalog = args.catalog
    if not catalog.is_absolute():
        catalog = (repo_root / catalog).resolve()

    with catalog.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))

    selected = set(args.category)
    if selected:
        rows = [row for row in rows if row["category"] in selected]

    download_root = (
        repo_root / "3d modeling" / "non_shipwreck_object_catalog" / "downloads"
    )
    download_root.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"{args.auth_scheme} {args.token}",
            "User-Agent": "shipwreck-sonar-ai/underwater-object-catalog",
        }
    )

    status: list[dict[str, Any]] = []
    for row in rows:
        category = row["category"]
        uid = row["sketchfab_uid"]
        category_root = repo_root / "3d modeling" / category
        model_dir = download_root / category / uid
        scene_marker = model_dir / "scene_path.txt"

        try:
            category_root.joinpath("original_models").mkdir(parents=True, exist_ok=True)
            category_root.joinpath("preview_images").mkdir(parents=True, exist_ok=True)
            write_attribution(category_root, row)

            if model_dir.exists() and args.overwrite:
                shutil.rmtree(model_dir)
            model_dir.mkdir(parents=True, exist_ok=True)

            if scene_marker.exists() and not args.overwrite:
                scene = Path(scene_marker.read_text(encoding="utf-8").strip())
                if scene.exists():
                    print(f"[skip] {category}: {scene}")
                    status.append(
                        {"category": category, "status": "already_downloaded", "scene": str(scene)}
                    )
                    continue

            payload = request_download_metadata(session, uid)
            package_type, package = choose_package(payload)

            with tempfile.TemporaryDirectory(prefix=f"sketchfab-{uid}-") as temp:
                archive_path = Path(temp) / f"{uid}.zip"
                download_file(session, package["url"], archive_path)
                with zipfile.ZipFile(archive_path) as archive:
                    safe_extract(archive, model_dir)

            scene = find_scene_file(model_dir).resolve()
            scene_marker.write_text(str(scene), encoding="utf-8")
            status.append(
                {
                    "category": category,
                    "status": "downloaded",
                    "package": package_type,
                    "scene": str(scene),
                    "reported_size": package.get("size"),
                }
            )
            print(f"[ok] {category}: {scene}")
        except Exception as error:
            status.append(
                {"category": category, "status": "error", "error": str(error)}
            )
            print(f"[error] {category}: {error}", file=sys.stderr)

    status_path = download_root / "download_status.json"
    status_path.write_text(
        json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    failures = sum(item["status"] == "error" for item in status)
    print(f"Wrote {status_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
