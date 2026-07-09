# START HERE

This repo is for **my Artemis Lab shipwreck sonar project**.

I do not need to understand every folder right now.

## What to use

Use only these files first:

```text
START_HERE.md
run_01_make_fake_sonar_data.py
run_02_view_fake_sonar_data.py
run_03_train_ai_model.py
run_04_view_ai_predictions.py
```

Ignore these folders for now:

```text
src/
docs/
```

`src/` just stores the internal code that the run files use.

## What the steps mean

### Step 1

```text
run_01_make_fake_sonar_data.py
```

Creates fake side-scan-sonar-like images and masks.

Output:

```text
data/toy_sim/images/
data/toy_sim/masks/
```

### Step 2

```text
run_02_view_fake_sonar_data.py
```

Creates one picture so I can check the fake data.

Output:

```text
results/toy_samples_grid.png
```

### Step 3

```text
run_03_train_ai_model.py
```

Trains a small U-Net AI model.

Input:

```text
data/toy_sim/images/
data/toy_sim/masks/
```

Output:

```text
results/toy_unet/best_unet.pt
```

### Step 4

```text
run_04_view_ai_predictions.py
```

Creates one picture showing the AI result.

Output:

```text
results/toy_unet/predictions_grid.png
```

## Run commands on Windows PowerShell

Go to the repo folder:

```powershell
cd "F:\Artemis Lab\shipwreck-sonar-ai"
```

Install packages:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

Run the four steps:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_01_make_fake_sonar_data.py
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_02_view_fake_sonar_data.py
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_03_train_ai_model.py
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_04_view_ai_predictions.py
```

Then open:

```text
results/toy_samples_grid.png
results/toy_unet/predictions_grid.png
```

## Simple mental model

```text
make fake sonar data
→ look at fake data
→ train AI
→ look at AI prediction
```

That is all for now.
