"""PyTorch dataset for toy sonar image-mask pairs."""

from __future__ import annotations

from pathlib import Path

import cv2
import torch
from torch.utils.data import Dataset


class ToySonarDataset(Dataset):
    """Load synthetic sonar images and binary masks.

    Expected folder structure:
        data/toy_sim/
          images/image_000001.png
          masks/mask_000001.png

    Returns:
        image: FloatTensor, shape [1, H, W], range [0, 1]
        mask:  FloatTensor, shape [1, H, W], values 0 or 1
        sample_id: str
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.images_dir = self.data_dir / "images"
        self.masks_dir = self.data_dir / "masks"

        if not self.images_dir.exists():
            raise FileNotFoundError(f"Missing images directory: {self.images_dir}")
        if not self.masks_dir.exists():
            raise FileNotFoundError(f"Missing masks directory: {self.masks_dir}")

        self.image_paths = sorted(self.images_dir.glob("image_*.png"))
        if not self.image_paths:
            raise FileNotFoundError(f"No images found in {self.images_dir}")

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, str]:
        image_path = self.image_paths[idx]
        sample_id = image_path.stem.replace("image_", "")
        mask_path = self.masks_dir / f"mask_{sample_id}.png"

        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        if mask is None:
            raise ValueError(f"Could not read mask: {mask_path}")

        image_t = torch.from_numpy(image).float().unsqueeze(0) / 255.0
        mask_t = torch.from_numpy((mask > 0).astype("float32")).unsqueeze(0)
        return image_t, mask_t, sample_id
