"""AI4Shipwrecks dataset loader.

This loader tries to pair sonar images with mask/label files recursively.
It is intentionally flexible because downloaded datasets often use different folder names.
"""

from __future__ import annotations

import re
from pathlib import Path

import cv2
import torch
from torch.utils.data import Dataset

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
MASK_WORDS = (
    "mask",
    "masks",
    "label",
    "labels",
    "annotation",
    "annotations",
    "segmentation",
    "segmentations",
    "gt",
    "groundtruth",
    "ground_truth",
)
IMAGE_WORDS = ("image", "images", "img", "sonar", "sss")


def _is_image_file(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def _looks_like_mask(path: Path) -> bool:
    text = str(path).lower()
    return any(word in text for word in MASK_WORDS)


def _looks_like_image(path: Path) -> bool:
    text = str(path).lower()
    return any(word in text for word in IMAGE_WORDS) and not _looks_like_mask(path)


def _normalize_key(path: Path) -> str:
    text = path.stem.lower()
    text = re.sub(r"(mask|masks|label|labels|annotation|annotations|segmentation|segmentations|gt|groundtruth|ground_truth)", "", text)
    text = re.sub(r"(image|images|img|sonar|sss)", "", text)
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def find_pairs(root: str | Path) -> list[tuple[Path, Path]]:
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"Data directory does not exist: {root}")

    files = [p for p in root.rglob("*") if p.is_file() and _is_image_file(p)]
    if not files:
        raise FileNotFoundError(f"No image files found under: {root}")

    mask_files = [p for p in files if _looks_like_mask(p)]
    image_files = [p for p in files if p not in mask_files and _looks_like_image(p)]

    if not image_files:
        image_files = [p for p in files if p not in mask_files]

    mask_by_key: dict[str, Path] = {}
    for mask in mask_files:
        key = _normalize_key(mask)
        if key:
            mask_by_key[key] = mask

    pairs: list[tuple[Path, Path]] = []
    used_masks: set[Path] = set()

    for image in image_files:
        key = _normalize_key(image)
        mask = mask_by_key.get(key)
        if mask is not None and mask not in used_masks:
            pairs.append((image, mask))
            used_masks.add(mask)

    # Fallback: if one image folder and one mask folder have the same number of files,
    # pair them by sorted order. This is common in simple segmentation datasets.
    if not pairs and image_files and mask_files and len(image_files) == len(mask_files):
        pairs = list(zip(sorted(image_files), sorted(mask_files)))

    if not pairs:
        raise FileNotFoundError(
            f"No image-mask pairs found. Found {len(files)} image-like files, "
            f"{len(image_files)} possible images, and {len(mask_files)} possible masks."
        )

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
