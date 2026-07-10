# Shipwreck Sonar AI

This repository starts with a **toy 2D side-scan-sonar simulator** for shipwreck candidate segmentation.

The long-term goal is to build an AI/computer vision pipeline that can look at sonar images and identify suspicious underwater regions that may be shipwrecks or underwater cultural heritage candidates.

## Current Stage

**Stage 1: Toy 2D simulation**

The simulator creates synthetic grayscale sonar-like images with:

- noisy seabed background
- bright shipwreck-like object body
- dark acoustic shadow
- optional partial burial / weak contrast
- automatic ground-truth segmentation mask

Each generated sample contains:

```text
image_0001.png  # synthetic sonar-like image
mask_0001.png   # white = shipwreck body, black = background
```

The acoustic shadow is included in the sonar image but **not** in the mask.

## Why this simulator exists

Real shipwreck sonar data is limited and difficult to label. This toy simulator is not a full physics-based ocean simulator. Instead, it is a simple synthetic image generator used to test the image-to-mask segmentation pipeline before integrating AI4Shipwrecks and more advanced simulators.

## Planned Pipeline

```text
Toy 2D simulator
→ U-Net segmentation baseline
→ AI4Shipwrecks real-data benchmark
→ Synthetic + real data comparison
→ Korean wooden shipwreck adaptation
→ HoloOcean / Stonefish simulator investigation
```

## Quick Start

Install requirements:

```bash
pip install -r requirements.txt
```

Generate 100 toy sonar samples:

```bash
python src/toy_simulator/generate_dataset.py --num 100 --out-dir data/toy_sim --seed 42
```

Visualize samples:

```bash
python src/toy_simulator/visualize_samples.py --data-dir data/toy_sim --num 8 --out results/toy_samples_grid.png
```

## Repository Structure

```text
shipwreck-sonar-ai/
  src/
    toy_simulator/
      generate_dataset.py
      visualize_samples.py
  data/
    toy_sim/
      images/
      masks/
  results/
```

The `data/` and `results/` folders are ignored by Git because generated data can become large.

## Next Milestone

1. Generate 100 to 500 synthetic image-mask pairs.
2. Check whether the image, mask, and acoustic shadow are visually reasonable.
3. Train a simple U-Net model on the synthetic data.
4. Add AI4Shipwrecks as the real side-scan sonar benchmark.
