# Shipwreck database

The repository contains a machine-readable database for the current FBX shipwreck models.

## Size and orientation files

- `shipwreck_size_orientation_metadata.csv` contains manually curated identity and real-world target dimensions.
- `generated/shipwreck_size_orientation.csv` is the main table for spreadsheet and simulation use.
- `generated/shipwreck_size_orientation.json` contains the same records in structured JSON after the automatic scan runs.
- `scan_shipwreck_fbx.py` imports every FBX in Blender and measures its combined world-space bounding box.
- `.github/workflows/build-shipwreck-size-orientation.yml` refreshes the generated database whenever a shipwreck FBX or metadata row changes.

## Coordinate convention

All models should ultimately use:

- `+X`: bow / forward
- `+Y`: port / left / width
- `+Z`: up

The scanner identifies the longest, middle, and shortest bounding-box axes and calculates a recommended pre-rotation into this convention. This is an axis-based estimate only. It cannot know which end is the bow or whether the smallest axis truly points upward, so both signs must be reviewed visually before marking a model simulation-ready.

## Simulation placement ranges

The database uses the existing synthetic-data configuration:

- yaw: `0°` to `360°`
- pitch: `-12°` to `12°`
- roll: `-8°` to `8°`

## Updating dimensions

Edit only `shipwreck_size_orientation_metadata.csv` for manual corrections. Leave unknown measurements blank rather than estimating them. The GitHub Actions workflow preserves those values while refreshing FBX measurements and scale calculations.
