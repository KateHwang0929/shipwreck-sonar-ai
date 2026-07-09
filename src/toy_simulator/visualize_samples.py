"""Visualize toy sonar image-mask pairs.

Example:
    python src/toy_simulator/visualize_samples.py \
        --data-dir data/toy_sim \
        --num 8 \
        --out results/toy_samples_grid.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


def overlay_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Create a simple RGB overlay: sonar image + mask highlight."""
    image_norm = image.astype(np.float32) / 255.0
    rgb = np.stack([image_norm, image_norm, image_norm], axis=-1)

    mask_bool = mask > 0
    overlay = rgb.copy()
    overlay[mask_bool, 0] = 1.0
    overlay[mask_bool, 1] = 0.25 * overlay[mask_bool, 1]
    overlay[mask_bool, 2] = 0.25 * overlay[mask_bool, 2]
    return np.clip(overlay, 0, 1)


def load_pairs(data_dir: Path, num: int) -> list[tuple[Path, Path]]:
    images_dir = data_dir / "images"
    masks_dir = data_dir / "masks"

    if not images_dir.exists() or not masks_dir.exists():
        raise FileNotFoundError(
            f"Expected {images_dir} and {masks_dir}. Run generate_dataset.py first."
        )

    image_paths = sorted(images_dir.glob("image_*.png"))[:num]
    pairs = []
    for image_path in image_paths:
        sample_id = image_path.stem.replace("image_", "")
        mask_path = masks_dir / f"mask_{sample_id}.png"
        if mask_path.exists():
            pairs.append((image_path, mask_path))

    if not pairs:
        raise FileNotFoundError("No image-mask pairs found.")
    return pairs


def visualize(data_dir: Path, num: int, out: Path) -> None:
    pairs = load_pairs(data_dir, num)
    rows = len(pairs)
    fig, axes = plt.subplots(rows, 3, figsize=(9, 3 * rows))

    if rows == 1:
        axes = np.expand_dims(axes, axis=0)

    for row, (image_path, mask_path) in enumerate(pairs):
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

        if image is None or mask is None:
            raise ValueError(f"Could not read {image_path} or {mask_path}")

        axes[row, 0].imshow(image, cmap="gray")
        axes[row, 0].set_title(image_path.name)
        axes[row, 0].axis("off")

        axes[row, 1].imshow(mask, cmap="gray")
        axes[row, 1].set_title(mask_path.name)
        axes[row, 1].axis("off")

        axes[row, 2].imshow(overlay_mask(image, mask))
        axes[row, 2].set_title("overlay")
        axes[row, 2].axis("off")

    out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print(f"Saved visualization to: {out}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize toy sonar image-mask pairs.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/toy_sim"), help="Dataset directory.")
    parser.add_argument("--num", type=int, default=8, help="Number of samples to visualize.")
    parser.add_argument("--out", type=Path, default=Path("results/toy_samples_grid.png"), help="Output figure path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    visualize(data_dir=args.data_dir, num=args.num, out=args.out)


if __name__ == "__main__":
    main()
