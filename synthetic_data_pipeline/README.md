# Korean Shipwreck Synthetic Data Pipeline

A researched Korean shipwreck database plus a reproducible HoloOcean synthetic-data generator.

The pipeline is designed to support this workflow:

```text
Korean shipwreck catalog + repository FBX registry
                         |
                         v
               randomized scene manifest
                         |
                         v
            packaged HoloOcean custom world
                         |
                         v
       RGB + depth + semantic mask + sonar + pose
                         |
                         v
          per-scene metadata and training dataset
```

## Included

- 14 Korean or Korea-excavated wreck records from official National Research Institute of Maritime Heritage pages
- 11 FBX variants already represented in this repository
- UTF-8 CSV research catalog and model registry
- SQLite database builder
- reproducible object, vehicle, sensor, and environment parameter sampling
- HoloOcean scenario generation
- RGB, depth, semantic-segmentation, raycast imaging-sonar, pose, and metadata saving
- dry-run mode that works before Unreal packaging is complete

The two Turtle Ship assets are kept as historical references and excluded by the default archaeological-wreck filter.

## Files

```text
synthetic_data_pipeline/
├── README.md
├── UNREAL_SETUP.md
├── config.json
├── korean_shipwreck_catalog.csv
├── model_registry.csv
├── pipeline.py
├── requirements.txt
└── generated/                 # created at runtime
```

## Quick start

Run all commands from the repository root.

### 1. Validate the database

```powershell
python ".\synthetic_data_pipeline\pipeline.py" validate
```

Expected:

```text
Catalog records: 14
Registered FBX assets: 11
Validation passed
```

### 2. Build the SQLite database

```powershell
python ".\synthetic_data_pipeline\pipeline.py" build-db
```

Output:

```text
synthetic_data_pipeline/generated/korean_shipwrecks.sqlite
```

### 3. Generate randomized scenes

When the repository FBX files are available:

```powershell
python ".\synthetic_data_pipeline\pipeline.py" manifest `
  --repo-root "." `
  --num-scenes 1000
```

For planning before the FBX files are present locally:

```powershell
python ".\synthetic_data_pipeline\pipeline.py" manifest `
  --repo-root "." `
  --num-scenes 100 `
  --allow-missing-assets
```

The output is `generated/scene_manifest.jsonl`. Each line stores the chosen model, wreck pose, vehicle pose, sonar settings, visibility, turbidity, current speed, burial fraction, and random seed sequence.

### 4. Test without HoloOcean

```powershell
python ".\synthetic_data_pipeline\pipeline.py" run `
  --dry-run `
  --limit 5
```

This writes complete scenario and metadata JSON files without launching Unreal.

### 5. Render the dataset

Complete `UNREAL_SETUP.md`, then install the runtime dependencies inside the Linux environment where HoloOcean is installed:

```bash
python -m pip install -r synthetic_data_pipeline/requirements.txt
```

Generate and run:

```bash
python synthetic_data_pipeline/pipeline.py manifest \
  --repo-root . \
  --num-scenes 1000

python synthetic_data_pipeline/pipeline.py run --resume
```

A rendered scene can contain:

```text
generated/dataset/scene_000001/
├── rgb.png
├── depth.npy
├── semantic.png
├── sonar.npy
├── sonar_preview.png
├── pose.npy
└── metadata.json
```

## Randomized variables

- FBX model and wreck variant
- wreck location, yaw, pitch, roll, and burial fraction
- AUV orbit angle, distance, height, roll, pitch, and yaw
- sonar range, azimuth, elevation, additive noise, and multiplicative noise
- visibility, turbidity, and current-speed parameters

The configuration is deterministic for a fixed seed, so an experiment can be reproduced.

## Important boundary

The database, manifest generator, scenario generator, data saver, and dry-run workflow are complete Python components. Actual rendering still requires a packaged custom HoloOcean Unreal world that contains the FBX assets. HoloOcean scenarios select a packaged world and configure agents and sensors. They do not import an arbitrary FBX directly from a normal filesystem path during runtime.

For full model switching and scene randomization, implement the optional `ConfigureShipwreckScene` world command described in `UNREAL_SETUP.md`, then set `runner.world_command.enabled` to `true` in `config.json`. Until that is done, visibility, turbidity, current, burial, and wreck-transform values are generated as metadata but do not automatically alter the Unreal world.

## Data quality and rights

Official dimensions are marked as remaining, estimated, or restored rather than treated as interchangeable. The repository models are image-generated approximations, not precision archaeological scans. Confirm source-image rights and institutional reuse conditions before publishing generated assets or a public dataset.
