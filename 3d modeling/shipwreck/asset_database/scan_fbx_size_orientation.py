#!/usr/bin/env python3
"""Measure every shipwreck FBX and build size/orientation CSV and JSON databases.

Run with Blender:
blender --background --python "3d modeling/shipwreck/asset_database/scan_fbx_size_orientation.py" -- \
  --models-dir "3d modeling/shipwreck/original_models" \
  --metadata "3d modeling/shipwreck/asset_database/shipwreck_size_orientation.csv" \
  --output-csv "3d modeling/shipwreck/asset_database/shipwreck_size_orientation.csv" \
  --output-json "3d modeling/shipwreck/asset_database/shipwreck_size_orientation.json"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

STANDARD_FORWARD = "+X"
STANDARD_LEFT = "+Y"
STANDARD_UP = "+Z"

OUTPUT_FIELDS = [
    "model_file", "ship_id", "ship_name_ko", "ship_name_en", "variant",
    "asset_category", "target_length_m", "target_width_m", "target_height_m",
    "size_source_url", "size_source_note", "file_size_bytes", "file_sha256",
    "mesh_object_count", "vertex_count", "polygon_count",
    "bbox_x_units", "bbox_y_units", "bbox_z_units",
    "model_length_units", "model_width_units", "model_height_units",
    "current_length_axis", "current_width_axis", "current_height_axis",
    "recommended_rotate_x_deg", "recommended_rotate_y_deg",
    "recommended_rotate_z_deg", "uniform_scale_m_per_unit",
    "scaled_width_from_model_m", "scaled_height_from_model_m",
    "simulation_forward_axis", "simulation_left_axis", "simulation_up_axis",
    "default_yaw_deg", "default_pitch_deg", "default_roll_deg",
    "placement_yaw_min_deg", "placement_yaw_max_deg",
    "placement_pitch_min_deg", "placement_pitch_max_deg",
    "placement_roll_min_deg", "placement_roll_max_deg",
    "bow_direction_review_required", "up_direction_review_required",
    "orientation_status", "measurement_status", "measured_at_utc", "notes",
]


def parse_arguments() -> argparse.Namespace:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser.parse_args(args)


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def import_fbx(path: Path) -> None:
    if hasattr(bpy.ops.wm, "fbx_import"):
        bpy.ops.wm.fbx_import(filepath=str(path))
    else:
        bpy.ops.import_scene.fbx(filepath=str(path))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def number(value: str | None) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def axis_name(vector: Vector) -> str:
    values = list(vector)
    index = max(range(3), key=lambda i: abs(values[i]))
    sign = "+" if values[index] >= 0 else "-"
    return sign + "XYZ"[index]


def rounded(value: float | None, digits: int = 6):
    if value is None:
        return None
    result = round(float(value), digits)
    return 0.0 if abs(result) < 10 ** (-digits) else result


def measure(path: Path) -> dict:
    clean_scene()
    import_fbx(path)
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not objects:
        raise RuntimeError("FBX contains no mesh objects")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    minimum = Vector((math.inf, math.inf, math.inf))
    maximum = Vector((-math.inf, -math.inf, -math.inf))
    vertices = 0
    polygons = 0

    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        vertices += len(evaluated.data.vertices)
        polygons += len(evaluated.data.polygons)
        for corner in evaluated.bound_box:
            point = evaluated.matrix_world @ Vector(corner)
            minimum.x = min(minimum.x, point.x)
            minimum.y = min(minimum.y, point.y)
            minimum.z = min(minimum.z, point.z)
            maximum.x = max(maximum.x, point.x)
            maximum.y = max(maximum.y, point.y)
            maximum.z = max(maximum.z, point.z)

    dimensions = {
        "X": maximum.x - minimum.x,
        "Y": maximum.y - minimum.y,
        "Z": maximum.z - minimum.z,
    }
    if not all(math.isfinite(value) and value > 0 for value in dimensions.values()):
        raise RuntimeError(f"Invalid combined bounding box: {dimensions}")

    ordered = sorted(dimensions, key=lambda axis: dimensions[axis], reverse=True)
    length_axis, width_unsigned, height_axis = ordered
    basis = {
        "X": Vector((1.0, 0.0, 0.0)),
        "Y": Vector((0.0, 1.0, 0.0)),
        "Z": Vector((0.0, 0.0, 1.0)),
    }
    length_vector = basis[length_axis]
    height_vector = basis[height_axis]
    width_vector = height_vector.cross(length_vector)
    rotation = Matrix((length_vector, width_vector, height_vector))
    euler = rotation.to_euler("XYZ")

    return {
        "mesh_object_count": len(objects),
        "vertex_count": vertices,
        "polygon_count": polygons,
        "bbox_x_units": rounded(dimensions["X"]),
        "bbox_y_units": rounded(dimensions["Y"]),
        "bbox_z_units": rounded(dimensions["Z"]),
        "model_length_units": rounded(dimensions[length_axis]),
        "model_width_units": rounded(dimensions[width_unsigned]),
        "model_height_units": rounded(dimensions[height_axis]),
        "current_length_axis": "+" + length_axis,
        "current_width_axis": axis_name(width_vector),
        "current_height_axis": "+" + height_axis,
        "recommended_rotate_x_deg": rounded(math.degrees(euler.x), 3),
        "recommended_rotate_y_deg": rounded(math.degrees(euler.y), 3),
        "recommended_rotate_z_deg": rounded(math.degrees(euler.z), 3),
    }


def base_record(metadata: dict[str, str], filename: str, measured_at: str) -> dict:
    row = {field: "" for field in OUTPUT_FIELDS}
    row.update(metadata)
    row["model_file"] = filename
    row.update({
        "simulation_forward_axis": STANDARD_FORWARD,
        "simulation_left_axis": STANDARD_LEFT,
        "simulation_up_axis": STANDARD_UP,
        "default_yaw_deg": 0.0,
        "default_pitch_deg": 0.0,
        "default_roll_deg": 0.0,
        "placement_yaw_min_deg": 0.0,
        "placement_yaw_max_deg": 360.0,
        "placement_pitch_min_deg": -12.0,
        "placement_pitch_max_deg": 12.0,
        "placement_roll_min_deg": -8.0,
        "placement_roll_max_deg": 8.0,
        "bow_direction_review_required": "yes",
        "up_direction_review_required": "yes",
        "orientation_status": "axis_estimate_needs_visual_review",
        "measurement_status": "pending",
        "measured_at_utc": measured_at,
    })
    return row


def main() -> int:
    args = parse_arguments()
    models_dir = args.models_dir.resolve()
    metadata_path = args.metadata.resolve()
    measured_at = datetime.now(timezone.utc).isoformat()

    with metadata_path.open("r", newline="", encoding="utf-8-sig") as stream:
        metadata_rows = {
            row["model_file"]: row
            for row in csv.DictReader(stream)
            if row.get("model_file")
        }

    files = {path.name: path for path in sorted(models_dir.glob("*.fbx"))}
    all_names = sorted(set(files) | set(metadata_rows), key=str.casefold)
    records: list[dict] = []

    for filename in all_names:
        metadata = metadata_rows.get(filename, {
            "model_file": filename,
            "ship_id": Path(filename).stem.lower(),
            "ship_name_ko": "",
            "ship_name_en": Path(filename).stem,
            "variant": "unregistered",
            "asset_category": "unregistered",
            "target_length_m": "",
            "target_width_m": "",
            "target_height_m": "",
            "size_source_url": "",
            "size_source_note": "Automatically discovered FBX; metadata review required.",
            "notes": "",
        })
        row = base_record(metadata, filename, measured_at)
        path = files.get(filename)
        if path is None:
            row["measurement_status"] = "missing_fbx"
            row["orientation_status"] = "not_measured"
            records.append(row)
            continue

        row["file_size_bytes"] = path.stat().st_size
        row["file_sha256"] = digest(path)
        try:
            row.update(measure(path))
            target_length = number(row.get("target_length_m"))
            model_length = number(str(row.get("model_length_units", "")))
            scale = target_length / model_length if target_length and model_length else None
            row["uniform_scale_m_per_unit"] = rounded(scale, 9)
            if scale:
                row["scaled_width_from_model_m"] = rounded(number(str(row["model_width_units"])) * scale)
                row["scaled_height_from_model_m"] = rounded(number(str(row["model_height_units"])) * scale)
            row["measurement_status"] = "measured"
        except Exception as exc:
            row["measurement_status"] = "error"
            row["orientation_status"] = "not_measured"
            row["notes"] = (row.get("notes", "") + f" Scanner error: {exc}").strip()
        records.append(row)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    args.output_json.write_text(json.dumps({
        "database_name": "Shipwreck Size and Orientation Database",
        "record_count": len(records),
        "coordinate_convention": {"forward": STANDARD_FORWARD, "left_width": STANDARD_LEFT, "up": STANDARD_UP},
        "orientation_warning": "Bounding-box axes are automatic estimates. Confirm bow and up signs visually before simulation.",
        "generated_at_utc": measured_at,
        "records": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(records)} records to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
