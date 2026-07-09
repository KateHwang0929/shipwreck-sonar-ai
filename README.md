# Shipwreck Sonar AI

This is my personal Artemis Lab repo.

Right now, I only need to run the simple files in the main folder.

## Use These Files First

```text
START_HERE.md
run_01_make_fake_sonar_data.py
run_02_view_fake_sonar_data.py
run_03_train_ai_model.py
run_04_view_ai_predictions.py
```

## Ignore These For Now

```text
src/
docs/
PROJECT_STATUS.md
```

`src/` means source code. It is the internal code folder. I do not need to open it yet.

## What I Am Doing

```text
make fake sonar data
→ view fake sonar data
→ train AI model
→ view AI predictions
```

## Run on Windows PowerShell

Go to the repo:

```powershell
cd "F:\Artemis Lab\shipwreck-sonar-ai"
```

Install packages:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

Run step 1:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_01_make_fake_sonar_data.py
```

Run step 2:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_02_view_fake_sonar_data.py
```

Run step 3:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_03_train_ai_model.py
```

Run step 4:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_04_view_ai_predictions.py
```

## Open These Results

```text
results/toy_samples_grid.png
results/toy_unet/predictions_grid.png
```

## What Each Step Means

| File | Meaning |
|---|---|
| `run_01_make_fake_sonar_data.py` | makes fake sonar images and masks |
| `run_02_view_fake_sonar_data.py` | makes a picture so I can check the fake data |
| `run_03_train_ai_model.py` | trains the U-Net AI model |
| `run_04_view_ai_predictions.py` | makes a picture of the AI prediction |

## Later, Not Now

Later I will add:

```text
AI4Shipwrecks real dataset
harder fake data
rocks / fishing gear / pottery scatter
HoloOcean / Stonefish notes
```

For now, just run the four simple files.
