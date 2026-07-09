"""Generate a toy 2D side-scan-sonar-style shipwreck segmentation dataset.

This is intentionally simple. It is not a physics-accurate acoustic simulator.
The goal is to create synthetic image-mask pairs so we can test an
image-to-mask segmentation pipeline before moving to AI4Shipwrecks.

Generated files:
    data/toy_sim/images/image_000001.png
    data/toy_sim/masks/mask_000001.png
    data/toy_sim/metadata.jsonl

Mask convention:
    255 = shipwreck body
      0 = background

The acoustic shadow is visible in the image but is not included in the mask.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm


@dataclass
class SampleMetadata:
    image_id: str
    object_type: str
    center_x: int
    center_y: int
    length: float
    width: float
    angle_degrees: float
    shadow_length: int
    shadow_direction: int
    noise_level: float
    burial_level: float
    contrast_scale: float


def ensure_dirs(out_dir: Path) -> tuple[Path, Path]:
    images_dir = out_dir / "images"
    masks_dir = out_dir / "masks"
    images_dir.mkdir(parents=True, exist_ok=True)
    masks_dir.mkdir(parents=True, exist_ok=True)
    return images_dir, masks_dir


def make_seabed_background(size: int, rng: np.random.Generator) -> np.ndarray:
    """Create gray seabed texture with noise, blur, and weak ripple patterns."""
    base_intensity = rng.uniform(85, 130)
    noise_std = rng.uniform(8, 22)
    img = rng.normal(base_intensity, noise_std, (size, size)).astype(np.float32)

    # Smooth low-frequency texture, similar to sediment variation.
    low_freq = rng.normal(0, 1, (size, size)).astype(np.float32)
    low_freq = cv2.GaussianBlur(low_freq, (0, 0), sigmaX=rng.uniform(8, 22))
    low_freq = low_freq / (np.std(low_freq) + 1e-6)
    img += low_freq * rng.uniform(5, 16)

    # Optional weak seabed ripple texture.
    yy, xx = np.mgrid[0:size, 0:size]
    theta = rng.uniform(0, np.pi)
    freq = rng.uniform(0.03, 0.09)
    ripple = np.sin((xx * np.cos(theta) + yy * np.sin(theta)) * freq)
    img += ripple * rng.uniform(2, 8)

    img = cv2.GaussianBlur(img, (5, 5), sigmaX=rng.uniform(0.4, 1.2))
    return np.clip(img, 0, 255)


def rotated_irregular_polygon(
    center_x: int,
    center_y: int,
    length: float,
    width: float,
    angle_rad: float,
    rng: np.random.Generator,
    n_points: int = 20,
) -> np.ndarray:
    """Create a rotated irregular shipwreck-like polygon."""
    points = []
    for t in np.linspace(0, 2 * np.pi, n_points, endpoint=False):
        # Ellipse-like base shape with random roughness.
        radius_scale = rng.uniform(0.72, 1.22)
        x = (length / 2.0) * np.cos(t) * radius_scale
        y = (width / 2.0) * np.sin(t) * rng.uniform(0.65, 1.35)

        # Rotate.
        xr = x * np.cos(angle_rad) - y * np.sin(angle_rad)
        yr = x * np.sin(angle_rad) + y * np.cos(angle_rad)
        points.append([center_x + xr, center_y + yr])

    return np.array(points, dtype=np.int32)


def make_shipwreck_mask(size: int, rng: np.random.Generator) -> tuple[np.ndarray, dict]:
    """Create binary mask for one irregular shipwreck-like body."""
    margin = int(size * 0.18)
    center_x = int(rng.integers(margin, size - margin))
    center_y = int(rng.integers(margin, size - margin))
    length = float(rng.uniform(size * 0.16, size * 0.38))
    width = float(rng.uniform(size * 0.035, size * 0.11))
    angle = float(rng.uniform(0, np.pi))

    mask = np.zeros((size, size), dtype=np.uint8)
    pts = rotated_irregular_polygon(center_x, center_y, length, width, angle, rng)
    cv2.fillPoly(mask, [pts], 255)

    # Add a few small broken pieces attached to or near the main wreck.
    if rng.random() < 0.55:
        num_pieces = int(rng.integers(1, 4))
        for _ in range(num_pieces):
            offset = rng.normal(0, [length * 0.25, width * 0.9])
            ox = offset[0] * np.cos(angle) - offset[1] * np.sin(angle)
            oy = offset[0] * np.sin(angle) + offset[1] * np.cos(angle)
            px = int(np.clip(center_x + ox, 0, size - 1))
            py = int(np.clip(center_y + oy, 0, size - 1))
            piece_len = rng.uniform(length * 0.08, length * 0.18)
            piece_width = rng.uniform(width * 0.35, width * 0.8)
            piece_angle = angle + rng.uniform(-0.8, 0.8)
            piece_pts = rotated_irregular_polygon(
                px, py, piece_len, piece_width, piece_angle, rng, n_points=10
            )
            cv2.fillPoly(mask, [piece_pts], 255)

    params = {
        "center_x": center_x,
        "center_y": center_y,
        "length": length,
        "width": width,
        "angle_rad": angle,
        "angle_degrees": float(np.degrees(angle)),
    }
    return mask, params


def make_shadow(mask: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, int, int]:
    """Create a dark acoustic shadow by shifting the object mask sideways."""
    size = mask.shape[0]
    shadow_direction = int(rng.choice([-1, 1]))
    shadow_length = int(rng.integers(size * 0.04, size * 0.16))
    dy = int(rng.integers(-3, 4))

    shadow = np.zeros_like(mask)
    for shift in range(2, shadow_length):
        matrix = np.float32([[1, 0, shadow_direction * shift], [0, 1, dy * shift / shadow_length]])
        shifted = cv2.warpAffine(mask, matrix, (size, size), borderValue=0)
        shadow = np.maximum(shadow, shifted)

    # Spread and soften the shadow.
    kernel_size = int(rng.integers(3, 9))
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    shadow = cv2.dilate(shadow, kernel, iterations=1)
    shadow = np.where((shadow > 0) & (mask == 0), 255, 0).astype(np.uint8)
    return shadow, shadow_length, shadow_direction


def apply_object_and_shadow(
    background: np.ndarray,
    body_mask: np.ndarray,
    shadow_mask: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, float, float, float]:
    """Blend object reflection, acoustic shadow, noise, and burial into image."""
    img = background.copy().astype(np.float32)

    noise_level = float(rng.uniform(0.04, 0.18))
    burial_level = float(rng.uniform(0.0, 0.45))
    contrast_scale = float(rng.uniform(0.65, 1.25))

    # Dark acoustic shadow. This is a major clue in side-scan sonar images.
    shadow_pixels = shadow_mask > 0
    shadow_darkness = rng.uniform(0.18, 0.55)
    img[shadow_pixels] *= shadow_darkness

    # Bright acoustic reflection from the object body.
    body_pixels = body_mask > 0
    object_brightness = rng.uniform(165, 240) * contrast_scale
    texture = rng.normal(0, 15, img.shape).astype(np.float32)
    img[body_pixels] = object_brightness + texture[body_pixels]

    # Partial burial / weak contrast: blend some object pixels back toward background.
    if burial_level > 0:
        burial_noise = rng.random(img.shape)
        buried = body_pixels & (burial_noise < burial_level)
        img[buried] = 0.65 * background[buried] + 0.35 * img[buried]

    # Speckle-like sonar noise.
    speckle = rng.normal(0, noise_level, img.shape).astype(np.float32)
    img = img + img * speckle

    # Slight blur and clipping.
    if rng.random() < 0.8:
        img = cv2.GaussianBlur(img, (3, 3), sigmaX=rng.uniform(0.2, 0.9))

    img = np.clip(img, 0, 255)
    return img.astype(np.uint8), noise_level, burial_level, contrast_scale


def generate_sample(size: int, rng: np.random.Generator, image_id: str) -> tuple[np.ndarray, np.ndarray, SampleMetadata]:
    background = make_seabed_background(size, rng)
    body_mask, params = make_shipwreck_mask(size, rng)
    shadow_mask, shadow_length, shadow_direction = make_shadow(body_mask, rng)
    image, noise_level, burial_level, contrast_scale = apply_object_and_shadow(
        background, body_mask, shadow_mask, rng
    )

    metadata = SampleMetadata(
        image_id=image_id,
        object_type="shipwreck",
        center_x=params["center_x"],
        center_y=params["center_y"],
        length=params["length"],
        width=params["width"],
        angle_degrees=params["angle_degrees"],
        shadow_length=shadow_length,
        shadow_direction=shadow_direction,
        noise_level=noise_level,
        burial_level=burial_level,
        contrast_scale=contrast_scale,
    )
    return image, body_mask, metadata


def generate_dataset(num: int, size: int, out_dir: Path, seed: int) -> None:
    rng = np.random.default_rng(seed)
    images_dir, masks_dir = ensure_dirs(out_dir)
    metadata_path = out_dir / "metadata.jsonl"

    with metadata_path.open("w", encoding="utf-8") as f:
        for i in tqdm(range(num), desc="Generating toy sonar samples"):
            image_id = f"{i + 1:06d}"
            image, mask, metadata = generate_sample(size, rng, image_id)

            image_path = images_dir / f"image_{image_id}.png"
            mask_path = masks_dir / f"mask_{image_id}.png"
            cv2.imwrite(str(image_path), image)
            cv2.imwrite(str(mask_path), mask)
            f.write(json.dumps(asdict(metadata), ensure_ascii=False) + "\n")

    print(f"Generated {num} samples in: {out_dir}")
    print(f"Images: {images_dir}")
    print(f"Masks:  {masks_dir}")
    print(f"Metadata: {metadata_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate toy 2D side-scan-sonar shipwreck dataset.")
    parser.add_argument("--num", type=int, default=100, help="Number of samples to generate.")
    parser.add_argument("--image-size", type=int, default=256, help="Image size in pixels. Creates square images.")
    parser.add_argument("--out-dir", type=Path, default=Path("data/toy_sim"), help="Output dataset directory.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.num <= 0:
        raise ValueError("--num must be positive")
    if args.image_size < 64:
        raise ValueError("--image-size should be at least 64")
    generate_dataset(num=args.num, size=args.image_size, out_dir=args.out_dir, seed=args.seed)


if __name__ == "__main__":
    main()
