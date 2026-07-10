"""Check whether AI4Shipwrecks image-mask pairs can be found."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.datasets.ai4shipwrecks_dataset import find_pairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/ai4shipwrecks_raw"))
    parser.add_argument("--show", type=int, default=10)
    args = parser.parse_args()

    pairs = find_pairs(args.data_dir)
    print(f"Found {len(pairs)} image-mask pairs")
    for image_path, mask_path in pairs[: args.show]:
        print(f"IMAGE: {image_path}")
        print(f"MASK : {mask_path}")
        print()


if __name__ == "__main__":
    main()
