"""Evaluate a trained U-Net checkpoint on toy sonar data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.datasets.toy_dataset import ToySonarDataset
from src.models import UNet
from src.training.metrics import (
    dice_score_from_logits,
    iou_score_from_logits,
    precision_from_logits,
    recall_from_logits,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/toy_sim"))
    parser.add_argument("--checkpoint", type=Path, default=Path("results/toy_unet/best_unet.pt"))
    parser.add_argument("--batch-size", type=int, default=8)
    return parser.parse_args()


@torch.no_grad()
def main() -> None:
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dataset = ToySonarDataset(args.data_dir)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)

    model = UNet(in_channels=1, out_channels=1).to(device)
    model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    model.eval()

    totals = {"dice": 0.0, "iou": 0.0, "precision": 0.0, "recall": 0.0}
    count = 0
    for images, masks, _ids in loader:
        images = images.to(device)
        masks = masks.to(device)
        logits = model(images)
        batch = images.size(0)
        totals["dice"] += float(dice_score_from_logits(logits, masks).item()) * batch
        totals["iou"] += float(iou_score_from_logits(logits, masks).item()) * batch
        totals["precision"] += float(precision_from_logits(logits, masks).item()) * batch
        totals["recall"] += float(recall_from_logits(logits, masks).item()) * batch
        count += batch

    print("Evaluation metrics")
    for key, value in totals.items():
        print(f"{key}: {value / count:.4f}")


if __name__ == "__main__":
    main()
