# Shipwreck Sonar AI

Toy sonar simulation + U-Net segmentation.

## Run

```powershell
cd "F:\Artemis Lab\shipwreck-sonar-ai"
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt

& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/toy_simulator/generate_dataset.py --num 200 --out-dir data/toy_sim --seed 42
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/toy_simulator/visualize_samples.py --data-dir data/toy_sim --num 8 --out results/toy_samples_grid.png
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/train_unet.py --data-dir data/toy_sim --epochs 5 --batch-size 8 --out-dir results/toy_unet
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/visualize_predictions.py --data-dir data/toy_sim --checkpoint results/toy_unet/best_unet.pt --num 8 --out results/toy_unet/predictions_grid.png
```

## Open

```text
results/toy_samples_grid.png
results/toy_unet/predictions_grid.png
```

## Files

```text
src/toy_simulator/     make and view fake sonar data
src/training/          train and view U-Net predictions
src/models/            U-Net model
src/datasets/          data loader
```
