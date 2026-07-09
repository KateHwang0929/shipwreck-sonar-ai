# Shipwreck Sonar AI

Run these four files only:

```text
run_01_make_fake_sonar_data.py
run_02_view_fake_sonar_data.py
run_03_train_ai_model.py
run_04_view_ai_predictions.py
```

## Commands

```powershell
cd "F:\Artemis Lab\shipwreck-sonar-ai"
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_01_make_fake_sonar_data.py
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_02_view_fake_sonar_data.py
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_03_train_ai_model.py
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" run_04_view_ai_predictions.py
```

## Results to open

```text
results/toy_samples_grid.png
results/toy_unet/predictions_grid.png
```

## Meaning

```text
run_01 = make fake sonar data
run_02 = view fake sonar data
run_03 = train AI model
run_04 = view AI predictions
```

Ignore `src/` for now. It is just the internal code folder.
