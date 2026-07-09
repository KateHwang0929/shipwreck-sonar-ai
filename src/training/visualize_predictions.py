"""Visualize U-Net predictions on toy sonar data.

Run from the repository root after training:
    python src/training/visualize_predictions.py \
        --data-dir data/toy_sim \
        --checkpoint results/toy_unet/best_unet.pt \
        --num 8 \
        --out results/toy_unet/predictions_grid.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.datasets.toy_dataset import ToySonarDataset
from src.models import UNet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/toy_sim"))
    parser.add_argument("--checkpoint", type=Path, default=Path("results/toy_unet/best_unet.pt"))
    parser.add_argument("--num", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("results/toy_unet/predictions_grid.png"))
    parser.add_argument("--threshold", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dataset = ToySonarDataset(args.data_dir)
    model = UNet(in_channels=1, out_channels=1).to(device)
    state = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(state)
    model.eval()

    num = min(args.num, len(dataset))
    fig, axes = plt.subplots(num, 4, figsize=(12, 3 * num))
    if num == 1:
        axes = np.expand_dims(axes, axis=0)

    with torch.no_grad():
        for i in range(num):
            image, mask, sample_id = dataset[i]
            logits = model(image.unsqueeze(0).to(device))
            prob = torch.sigmoid(logits).squeeze().cpu().numpy()
            pred = (prob >= args.threshold).astype(np.float32)

            axes[i, 0].imshow(image.squeeze().numpy(), cmap="gray")
            axes[i, 0].set_title(f"image {sample_id}")
            axes[i, 0].axis("off")

            axes[i, 1].imshow(mask.squeeze().numpy(), cmap="gray")
            axes[i, 1].set_title("ground truth")
            axes[i, 1].axis("off")

            axes[i, 2].imshow(prob, cmap="gray", vmin=0, vmax=1)
            axes[i, 2].set_title("probability")
            axes[i, 2].axis("off")

            axes[i, 3].imshow(pred, cmap="gray", vmin=0, vmax=1)
            axes[i, 3].set_title("predicted mask")
            axes[i, 3].axis("off")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    fig.savefig(args.out, dpi=160)
    plt.close(fig)
    print(f"Saved prediction visualization to: {args.out}")


if __name__ == "__main__":
    main()
