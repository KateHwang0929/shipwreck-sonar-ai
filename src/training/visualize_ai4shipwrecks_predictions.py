"""Visualize AI4Shipwrecks U-Net predictions."""

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

from src.datasets.ai4shipwrecks_dataset import AI4ShipwrecksDataset
from src.models import UNet


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/ai4shipwrecks_raw"))
    parser.add_argument("--checkpoint", type=Path, default=Path("results/ai4shipwrecks_unet/best_unet.pt"))
    parser.add_argument("--out", type=Path, default=Path("results/ai4shipwrecks_unet/predictions_grid.png"))
    parser.add_argument("--num", type=int, default=8)
    parser.add_argument("--image-size", type=int, default=256)
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dataset = AI4ShipwrecksDataset(args.data_dir, image_size=args.image_size)

    model = UNet(in_channels=1, out_channels=1).to(device)
    model.load_state_dict(torch.load(args.checkpoint, map_location=device))
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
            axes[i, 0].set_title(sample_id)
            axes[i, 0].axis("off")

            axes[i, 1].imshow(mask.squeeze().numpy(), cmap="gray")
            axes[i, 1].set_title("ground truth")
            axes[i, 1].axis("off")

            axes[i, 2].imshow(prob, cmap="gray", vmin=0, vmax=1)
            axes[i, 2].set_title("probability")
            axes[i, 2].axis("off")

            axes[i, 3].imshow(pred, cmap="gray", vmin=0, vmax=1)
            axes[i, 3].set_title("prediction")
            axes[i, 3].axis("off")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    fig.savefig(args.out, dpi=160)
    plt.close(fig)
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
