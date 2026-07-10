"""AI4Shipwrecks dataset loader.

Searches recursively for image files and pairs each image with a matching mask/label file.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import torch
from torch.utils.data import Dataset

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
MASK_WORDS = ("mask", "label", "labels", "annotation", "annotations", "segmentation", "gt")
IMAGE_WORDS = ("image", "images", "sonar", "sss")


def _is_image_file(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def _looks_like_mask(path: Path) -> bool:
    text = str(path).lower()
    return any(word in text for word in MASK_WORDS)


def _looks_like_image(path: Path) -> bool:
    text = str(path).lower()
    return any(word in text for word in IMAGE_WORDS) and not _looks_like_mask(path)


def _clean_stem(stem: str) -> str:
    s = stem.lower()
    for token in ["_mask", "-mask", " mask", "_label", "-label", " label", "_gt", "-gt", " gt"]:
        s = s.replace(token, "")
    for token in ["_image", "-image", " image", "_img", "-img", " img"]:
        s = s.replace(token, "")
    return s


def find_pairs(root: str | Path) -> list[tuple[Path, Path]]:
    root = Path(root)
    files = [p for p in root.rglob("*") if p.is_file() and _is_image_file(p)]

    mask_files = [p for p in files if _looks_like_mask(p)]
    image_files = [p for p in files if p not in mask_files and _looks_like_image(p)]
    if not image_files:
        image_files = [p for p in files if p not in mask_files]

    mask_by_stem = {_clean_stem(p.stem): p for p in mask_files}
    pairs: list[tuple[Path, Path]] = []

    for image_path in image_files:
        mask_path = mask_by_stem.get(_clean_stem(image_path.stem))
        if mask_path is not None:
            pairs.append((image_path, mask_path))

    if not pairs:
        raise FileNotFoundError("No image-mask pairs found. Check folder names and mask filenames.")

    return sorted(pairs, key=lambda x: str(x[0]))


class AI4ShipwrecksDataset(Dataset):
    def __init__(self, data_dir: str | Path, image_size: int = 256) -> None:
        self.data_dir = Path(data_dir)
        self.image_size = image_size
        self.pairs = find_pairs(self.data_dir)

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, str]:
        image_path, mask_path = self.pairs[idx]
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)

        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        if mask is None:
            raise ValueError(f"Could not read mask: {mask_path}")

        image = cv2.resize(image, (self.image_size, self.image_size), interpolation=cv2.INTER_AREA)
        mask = cv2.resize(mask, (self.image_size, self.image_size), interpolation=cv2.INTER_NEAREST)

        image_t = torch.from_numpy(image).float().unsqueeze(0) / 255.0
        mask_t = torch.from_numpy((mask > 0).astype("float32")).unsqueeze(0)
        return image_t, mask_t, image_path.stem
