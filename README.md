# Shipwreck Sonar AI

Toy sonar + AI4Shipwrecks U-Net segmentation.

## Toy data

```powershell
cd "F:\Artemis Lab\shipwreck-sonar-ai"
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/toy_simulator/generate_dataset.py --num 200 --out-dir data/toy_sim --seed 42
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/toy_simulator/visualize_samples.py --data-dir data/toy_sim --num 8 --out results/toy_samples_grid.png
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/train_unet.py --data-dir data/toy_sim --epochs 5 --batch-size 8 --out-dir results/toy_unet
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/visualize_predictions.py --data-dir data/toy_sim --checkpoint results/toy_unet/best_unet.pt --num 8 --out results/toy_unet/predictions_grid.png
```

## AI4Shipwrecks

Put dataset here:

```text
data/ai4shipwrecks_raw/
```

Check pairs:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/inspect_ai4shipwrecks.py --data-dir data/ai4shipwrecks_raw
```

Train:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/train_ai4shipwrecks_unet.py --data-dir data/ai4shipwrecks_raw --epochs 10 --batch-size 4 --out-dir results/ai4shipwrecks_unet
```

View predictions:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" src/training/visualize_ai4shipwrecks_predictions.py --data-dir data/ai4shipwrecks_raw --checkpoint results/ai4shipwrecks_unet/best_unet.pt --num 8 --out results/ai4shipwrecks_unet/predictions_grid.png
```

Open:

```text
results/ai4shipwrecks_unet/predictions_grid.png
```
