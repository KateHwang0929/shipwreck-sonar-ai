"""Inspect AI4Shipwrecks folder and print found image-mask pairs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.datasets.ai4shipwrecks_dataset import IMAGE_EXTS, find_pairs


def print_tree(root: Path, max_items: int = 80) -> None:
    print(f"data dir: {root}")
    print(f"exists: {root.exists()}")
    if not root.exists():
        return

    items = list(root.rglob("*"))[:max_items]
    print("\nfirst files/folders:")
    for p in items:
        kind = "DIR " if p.is_dir() else "FILE"
        print(f"{kind}: {p.relative_to(root)}")

    image_files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    print(f"\nimage-like files: {len(image_files)}")
    for p in image_files[:20]:
        print(f"IMG?: {p.relative_to(root)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/ai4shipwrecks_raw"))
    parser.add_argument("--show", type=int, default=10)
    args = parser.parse_args()

    print_tree(args.data_dir)
    print("\ntrying to pair images and masks...")

    try:
        pairs = find_pairs(args.data_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("\nSend me the printed folder/file list above.")
        return

    print(f"Found {len(pairs)} image-mask pairs")
    for image_path, mask_path in pairs[: args.show]:
        print(f"IMAGE: {image_path}")
        print(f"MASK : {mask_path}")
        print()


if __name__ == "__main__":
    main()
