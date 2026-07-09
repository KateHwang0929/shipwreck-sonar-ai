# Project Status

This file is for tracking my own progress.

## Current Stage

**Stage 1: Toy 2D simulator + U-Net segmentation**

Goal:

```text
fake sonar image → U-Net → predicted shipwreck mask
```

## What Is Done

- Created repository structure
- Added toy 2D sonar image generator
- Added mask generation
- Added metadata generation
- Added sample visualization script
- Added PyTorch dataset loader
- Added U-Net model
- Added Dice / IoU / precision / recall metrics
- Added training script
- Added evaluation script
- Added prediction visualization script

## What I Need To Do Locally

Run these commands in PowerShell from the repo root:

```powershell
cd "F:\Artemis Lab\shipwreck-sonar-ai"
```

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/toy_simulator/generate_dataset.py --num 200 --out-dir data/toy_sim --seed 42
```

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/toy_simulator/visualize_samples.py --data-dir data/toy_sim --num 8 --out results/toy_samples_grid.png
```

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/train_unet.py --data-dir data/toy_sim --epochs 5 --batch-size 8 --out-dir results/toy_unet
```

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/visualize_predictions.py --data-dir data/toy_sim --checkpoint results/toy_unet/best_unet.pt --num 8 --out results/toy_unet/predictions_grid.png
```

## Files To Check

```text
results/toy_samples_grid.png
results/toy_unet/predictions_grid.png
```

## What Counts As Success

The first success condition is simple:

```text
The model can roughly predict the bright shipwreck body in the toy sonar images.
```

The prediction does not need to be perfect yet.

## Next After This Works

1. Make toy simulation harder.
2. Add false objects: rocks, fishing gear, pottery scatter.
3. Add AI4Shipwrecks dataset loader.
4. Train the same U-Net on real SSS images.
5. Compare toy simulation vs AI4Shipwrecks.
