# Shipwreck Asset Size Database

This folder contains a concise, size-focused reference for the shipwreck and historical ship assets used in the project.

## File

- `shipwreck_size_reference.csv`: reference length, width, and height values in metres

## Important distinction

The dimensions in the CSV are **target real-world reference dimensions**, not measurements automatically extracted from the FBX mesh.

- `remaining`: dimensions of surviving archaeological remains
- `estimated_reconstruction`: estimated original or reconstructed dimensions
- `restored`: dimensions based on a full reconstruction reference
- `unknown`: no verified scale has been assigned

The Turtle Ship assets are historical reference models rather than excavated shipwrecks. Their dimensions are intentionally blank until one specific reconstruction source is selected.

## Scaling a model

Measure the model's longest hull axis in Blender, then calculate:

```text
uniform_scale = target_length_m / current_model_length
```

After scaling:

1. Confirm that the longest axis actually represents bow-to-stern length.
2. Check width and height against the CSV.
3. Apply rotation and scale with `Ctrl + A` in Blender.
4. Record the verified dimensions before using the model in sonar simulation.

## Status values

- `reference_dimension`: all three reference dimensions are available
- `partial_reference_dimension`: one or more dimensions still need verification
- `needs_verification`: no verified real-world size has been assigned

The larger generated database under `database/generated/` remains unchanged. This folder is intended to be the quick asset-scaling reference located beside the shipwreck models.
