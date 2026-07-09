# Shipwreck Sonar AI

Personal research repository for the Artemis Lab project on AI-based shipwreck candidate detection from side-scan sonar images.

This repo is written for my own workflow first. It is not meant to be a polished public package yet.

## Current Goal

Build the first working pipeline:

```text
synthetic sonar-like image
→ ground-truth mask
→ U-Net segmentation model
→ predicted mask
→ Dice / IoU evaluation
```

The current target is **toy 2D simulation**, not full underwater physics.

## What This Repo Does Right Now

### 1. Toy 2D sonar simulation

Creates fake grayscale side-scan-sonar-like images with:

- gray/noisy seabed background
- bright irregular shipwreck-like body
- dark acoustic shadow
- weak contrast / partial burial
- automatic segmentation mask

Important:

```text
shadow = visible in sonar image
mask = shipwreck body only
```

### 2. U-Net toy segmentation

Trains a simple U-Net model on generated toy data.

Input:

```text
image_000001.png
```

Output:

```text
predicted shipwreck mask
```

Metrics:

```text
Dice, IoU, precision, recall
```

## What This Repo Does Not Do Yet

- It does not use AI4Shipwrecks yet.
- It does not simulate real underwater acoustics accurately.
- It does not use HoloOcean or Stonefish yet.
- It does not detect real Korean wooden shipwrecks yet.

Those are later stages.

## Folder Structure

```text
shipwreck-sonar-ai/
  README.md
  PROJECT_STATUS.md
  requirements.txt

  src/
    toy_simulator/
      generate_dataset.py
      visualize_samples.py

    datasets/
      toy_dataset.py

    models/
      unet.py

    training/
      metrics.py
      train_unet.py
      evaluate.py
      visualize_predictions.py

  docs/
    workflow.md
    glossary.md

  data/       # generated locally, ignored by Git
  results/    # generated locally, ignored by Git
```

## Quick Start on Windows PowerShell

Go to the repo:

```powershell
cd "F:\Artemis Lab\shipwreck-sonar-ai"
```

Install dependencies:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

Generate toy data:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/toy_simulator/generate_dataset.py --num 200 --out-dir data/toy_sim --seed 42
```

Visualize generated data:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/toy_simulator/visualize_samples.py --data-dir data/toy_sim --num 8 --out results/toy_samples_grid.png
```

Train U-Net:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/train_unet.py --data-dir data/toy_sim --epochs 5 --batch-size 8 --out-dir results/toy_unet
```

Evaluate:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/evaluate.py --data-dir data/toy_sim --checkpoint results/toy_unet/best_unet.pt
```

Visualize predictions:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/visualize_predictions.py --data-dir data/toy_sim --checkpoint results/toy_unet/best_unet.pt --num 8 --out results/toy_unet/predictions_grid.png
```

Open these files locally:

```text
results/toy_samples_grid.png
results/toy_unet/predictions_grid.png
```

## My Current Checklist

- [x] Create toy 2D sonar generator
- [x] Generate image-mask pairs
- [x] Add visualization script
- [x] Add U-Net model
- [x] Add training / evaluation scripts
- [ ] Run local training successfully
- [ ] Inspect predictions_grid.png
- [ ] Decide whether toy images are too easy or too unrealistic
- [ ] Add harder false positives: rocks, fishing gear, pottery scatter
- [ ] Add AI4Shipwrecks dataset loader

## Should I Run More Simulation Now?

Not yet in a huge way.

For now, run only:

```text
200 samples → train U-Net → check predictions
```

If the model works, then generate more samples like 500 or 1000. More simulation is only useful after the basic pipeline works.

## Research Direction

Toy simulation is only the starting point. The real research direction is:

```text
Toy simulation
→ AI4Shipwrecks baseline
→ synthetic vs real data comparison
→ Korean wooden shipwreck adaptation
→ HoloOcean / Stonefish simulator review
```
