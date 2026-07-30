#!/usr/bin/env python3
"""Generate one textured FBX per Mado ceramic image group with Meshy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API = "https://api.meshy.ai/openapi/v1/multi-image-to-3d"
PATTERN = re.compile(r"^(mado\d+-\d+)_(\d+)\.(png|jpe?g)$", re.I)
FAILURE = {"FAILED", "CANCELED", "CANCELLED", "EXPIRED"}


def arguments() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=here / "original_models")
    parser.add_argument("--output-dir", type=Path, default=here / "preview_images")
    parser.add_argument(
        "--repo", default=os.getenv("GITHUB_REPOSITORY", "KateHwang0929/shipwreck-sonar-ai")
    )
    parser.add_argument("--ref", default=os.getenv("GITHUB_SHA", "main"))
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--timeout-minutes", type=int, default=60)
    return parser.parse_args()


def groups_in(folder: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[tuple[int, Path]]] = {}
    for path in folder.iterdir():
        match = PATTERN.match(path.name) if path.is_file() else None
        if match:
            groups.setdefault(match.group(1).lower(), []).append((int(match.group(2)), path))
    result = {name: [p for _, p in sorted(items)] for name, items in groups.items()}
    invalid = {name: len(paths) for name, paths in result.items() if not 1 <= len(paths) <= 4}
    if invalid:
        raise ValueError(f"Meshy accepts 1-4 images per group; invalid groups: {invalid}")
    return dict(sorted(result.items()))


def request_json(url: str, key: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        url,
        data=data,
        method="POST" if payload is not None else "GET",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "shipwreck-sonar-ai/1.0",
        },
    )
    try:
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        raise RuntimeError(f"Meshy HTTP {exc.code}: {exc.read().decode(errors='replace')}") from exc
    except URLError as exc:
        raise RuntimeError(f"Meshy request failed: {exc.reason}") from exc


def download(url: str, target: Path) -> None:
    temporary = target.with_suffix(target.suffix + ".part")
    request = Request(url, headers={"User-Agent": "shipwreck-sonar-ai/1.0"})
    try:
        with urlopen(request, timeout=300) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(target)
    except (HTTPError, URLError) as exc:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download {target.name}: {exc}") from exc


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def wait_for_task(key: str, task_id: str, poll: int, timeout: int) -> dict:
    deadline = time.monotonic() + timeout * 60
    last_progress = object()
    while time.monotonic() < deadline:
        task = request_json(f"{API}/{task_id}", key)
        status = str(task.get("status", "UNKNOWN")).upper()
        progress = task.get("progress")
        if progress != last_progress:
            print(f"  {status}: {progress}%", flush=True)
            last_progress = progress
        if status == "SUCCEEDED":
            return task
        if status in FAILURE:
            message = task.get("task_error", {}).get("message", "unknown error")
            raise RuntimeError(f"Task {task_id} {status}: {message}")
        time.sleep(max(1, poll))
    raise TimeoutError(f"Task {task_id} exceeded {timeout} minutes")


def write_manifest(output: Path, group: str, task_id: str, images: list[Path], fbx: Path, preview: Path) -> None:
    path = output / "meshy_manifest.json"
    manifest = json.loads(path.read_text()) if path.exists() else {"models": {}}
    manifest.setdefault("models", {})[group] = {
        "task_id": task_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_images": [image.name for image in images],
        "fbx_file": fbx.name,
        "fbx_bytes": fbx.stat().st_size,
        "fbx_sha256": checksum(fbx),
        "preview_file": preview.name if preview.exists() else None,
    }
    manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    args = arguments()
    input_dir, output_dir = args.input_dir.resolve(), args.output_dir.resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(input_dir)
    repo_root = input_dir.parent.parent.parent
    groups = groups_in(input_dir)
    selected = {name.lower() for name in args.only}
    if selected:
        missing = selected - groups.keys()
        if missing:
            raise ValueError(f"Unknown groups: {', '.join(sorted(missing))}")
        groups = {name: images for name, images in groups.items() if name in selected}
    if not groups:
        raise RuntimeError("No Mado ceramic image groups found")

    key = os.getenv("MESHY_API_KEY", "").strip()
    if not args.dry_run and not key:
        raise RuntimeError("MESHY_API_KEY is not set")
    output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    for group, images in groups.items():
        urls = []
        for image in images:
            relative = image.relative_to(repo_root).as_posix()
            urls.append(
                f"https://raw.githubusercontent.com/{args.repo}/{quote(args.ref, safe='')}/{quote(relative, safe='/')}"
            )
        print(f"{group}: {len(images)} view(s)")
        for url in urls:
            print(f"  {url}")
        if args.dry_run:
            continue

        fbx = output_dir / f"{group}.fbx"
        preview = output_dir / f"{group}_preview.png"
        if fbx.exists() and not args.overwrite:
            print(f"  skipping existing {fbx.name}")
            continue
        try:
            created = request_json(
                API,
                key,
                {
                    "image_urls": urls,
                    "should_texture": True,
                    "enable_pbr": True,
                    "target_formats": ["fbx"],
                },
            )
            task_id = created.get("result")
            if not task_id:
                raise RuntimeError(f"No task ID returned: {created}")
            print(f"  task={task_id}")
            task = wait_for_task(key, task_id, args.poll_seconds, args.timeout_minutes)
            fbx_url = task.get("model_urls", {}).get("fbx")
            if not fbx_url:
                raise RuntimeError("Task succeeded without an FBX URL")
            download(fbx_url, fbx)
            if task.get("thumbnail_url"):
                download(task["thumbnail_url"], preview)
            write_manifest(output_dir, group, task_id, images, fbx, preview)
            print(f"  saved {fbx.name}")
        except Exception as exc:
            failures.append(f"{group}: {exc}")
            print(f"  ERROR: {exc}", file=sys.stderr)

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
