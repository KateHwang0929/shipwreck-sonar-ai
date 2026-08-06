# Non-shipwreck underwater object catalog

This addition expands the `3d modeling` dataset with discrete non-shipwreck targets. Each category is intended to contain one clearly identifiable object made primarily from one physical material.

## Selected categories

| Category | Object | Primary material |
|---|---|---|
| `rock` | Rock-Boulder | stone |
| `moss_clump` | Moss clump | moss/organic vegetation |
| `mud_pile` | Mud pile | mud |
| `driftwood` | Driftwood | wood |
| `seashell` | Sea Shell | calcium-carbonate shell |
| `concrete_block` | Concrete Block (Low Poly) | concrete |
| `brick` | Brick | fired clay |
| `metal_pipe` | Metal Pipe | metal |
| `concrete_pipe` | Large Concrete Pipe | concrete |
| `glass_bottle` | Glass Bottle | glass |
| `anchor` | Anchor | metal |
| `rope` | Coiled Rope | rope fiber |
| `plastic_crate` | Plastic Crate | plastic |
| `iron_chain` | Iron chain | iron |
| `ship_propeller` | Ship-Propeller | metal |
| `dead_coral` | Coral | calcium-carbonate coral skeleton |

## Folder convention

Each category has the same structure:

```text
3d modeling/<category>/
├── original_models/
│   └── <category>.fbx
└── preview_images/
    └── <category>.png
```

Empty folders are tracked with `.gitkeep` until the authenticated download and Blender conversion are run.

## Why model binaries are not committed yet

Sketchfab requires an authenticated user request before it returns a temporary download URL. Its download API returns converted glTF/GLB packages rather than source FBX files. For that reason, this branch contains:

1. A reviewed source catalog with model authors, URLs, licenses, and target paths.
2. The complete category folder structure.
3. An authenticated downloader for the selected Sketchfab models.
4. A Blender script that converts each downloaded glTF/GLB model to FBX and renders the PNG preview.

No preview image or FBX placeholder is fabricated. Run the workflow below with your own Sketchfab token to populate the folders.

## Run the workflow

Install the Python dependency:

```bash
python -m pip install -r "3d modeling/non_shipwreck_object_catalog/requirements.txt"
```

Set a Sketchfab access token without saving it in Git:

```bash
export SKETCHFAB_TOKEN="your_token_here"
```

On Windows PowerShell:

```powershell
$env:SKETCHFAB_TOKEN="your_token_here"
```

Download the selected models:

```bash
python "3d modeling/non_shipwreck_object_catalog/download_sketchfab_models.py" \
  --repo-root . \
  --catalog "3d modeling/non_shipwreck_object_catalog/model_catalog.csv"
```

Convert to FBX and render previews with Blender:

```bash
blender --background \
  --python "3d modeling/non_shipwreck_object_catalog/blender_convert_and_render.py" \
  -- \
  --repo-root . \
  --catalog "3d modeling/non_shipwreck_object_catalog/model_catalog.csv"
```

The Blender script joins imported mesh nodes into one logical object, reports material counts, exports the FBX, and renders a transparent 512 x 512 PNG. Review `validation_report.csv` before using an asset for simulation or training.

## Licensing and attribution

All selected model pages were listed as downloadable under Creative Commons Attribution when reviewed on 2026-08-06. Keep the author, source URL, and license information from `model_catalog.csv` with every redistributed or adapted asset. Recheck the model page before downloading because authors can change availability or metadata.

Do not commit API tokens, temporary download URLs, or unreviewed models.
