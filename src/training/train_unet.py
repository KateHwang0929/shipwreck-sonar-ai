"""Train U-Net on toy sonar image-mask pairs.

Run from the repository root:
    python src/training/train_unet.py --data-dir data/toy_sim --epochs 5
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, Subset
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.datasets.toy_dataset import ToySonarDataset
from src.models import UNet
from src.training.metrics import dice_score_from_logits, iou_score_from_logits


def make_split(n: int, val_fraction: float, seed: int) -> tuple[list[int], list[int]]:
    indices = list(range(n))
    random.Random(seed).shuffle(indices)
    val_size = max(1, int(n * val_fraction))
    return indices[val_size:], indices[:val_size]


def train_epoch(model: nn.Module, loader: DataLoader, optimizer: torch.optim.Optimizer, loss_fn: nn.Module, device: torch.device) -> float:
    model.train()
    total = 0.0
    for images, masks, _ids in tqdm(loader, desc="train", leave=False):
        images = images.to(device)
        masks = masks.to(device)
        optimizer.zero_grad()
        logits = model(images)
        loss = loss_fn(logits, masks)
        loss.backward()
        optimizer.step()
        total += float(loss.item()) * images.size(0)
    return total / len(loader.dataset)


@torch.no_grad()
def validate(model: nn.Module, loader: DataLoader, loss_fn: nn.Module, device: torch.device) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    total_dice = 0.0
    total_iou = 0.0
    count = 0
    for images, masks, _ids in tqdm(loader, desc="val", leave=False):
        images = images.to(device)
        masks = masks.to(device)
        logits = model(images)
        batch = images.size(0)
        total_loss += float(loss_fn(logits, masks).item()) * batch
        total_dice += float(dice_score_from_logits(logits, masks).item()) * batch
        total_iou += float(iou_score_from_logits(logits, masks).item()) * batch
        count += batch
    return {"loss": total_loss / count, "dice": total_dice / count, "iou": total_iou / count}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/toy_sim"))
    parser.add_argument("--out-dir", type=Path, default=Path("results/toy_unet"))
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    dataset = ToySonarDataset(args.data_dir)
    train_idx, val_idx = make_split(len(dataset), args.val_fraction, args.seed)
    train_loader = DataLoader(Subset(dataset, train_idx), batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(Subset(dataset, val_idx), batch_size=args.batch_size, shuffle=False)

    model = UNet(in_channels=1, out_channels=1).to(device)
    loss_fn = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    best_dice = -1.0

    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, loss_fn, device)
        val = validate(model, val_loader, loss_fn, device)
        print(
            f"epoch {epoch:03d} | train_loss {train_loss:.4f} | "
            f"val_loss {val['loss']:.4f} | val_dice {val['dice']:.4f} | val_iou {val['iou']:.4f}"
        )
        if val["dice"] > best_dice:
            best_dice = val["dice"]
            torch.save(model.state_dict(), args.out_dir / "best_unet.pt")

    print(f"Saved model: {args.out_dir / 'best_unet.pt'}")


if __name__ == "__main__":
    main()
