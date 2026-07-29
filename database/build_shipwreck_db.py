#utilized codex for this code

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def number(value: str | None, kind=float):
    value = (value or "").strip()
    return None if not value else kind(value)


def flag(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def file_stats(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "size_bytes": None, "size_mib": None, "sha256": None}

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)

    size = path.stat().st_size
    return {
        "exists": True,
        "size_bytes": size,
        "size_mib": round(size / 1048576, 4),
        "sha256": digest.hexdigest(),
    }


def glb_stats(path: Path) -> dict[str, Any]:
    empty = {
        "glb_parse_status": "missing",
        "mesh_count": None,
        "primitive_count": None,
        "vertex_count": None,
        "triangle_count": None,
        "material_count": None,
        "texture_count": None,
        "bbox_x_units": None,
        "bbox_y_units": None,
        "bbox_z_units": None,
        "bbox_longest_units": None,
        "bbox_middle_units": None,
        "bbox_shortest_units": None,
    }
    if not path.is_file():
        return empty

    try:
        with path.open("rb") as stream:
            magic, version, total_length = struct.unpack("<4sII", stream.read(12))
            if magic != b"glTF" or version != 2:
                raise ValueError("Only GLB 2.0 is supported")
            if total_length != path.stat().st_size:
                raise ValueError("GLB file length does not match its header")

            document = None
            while stream.tell() < total_length:
                length, chunk_type = struct.unpack("<I4s", stream.read(8))
                data = stream.read(length)
                if chunk_type == b"JSON":
                    document = json.loads(data.decode("utf-8").rstrip("\x00 \t\r\n"))
                    break

        if document is None:
            raise ValueError("JSON chunk was not found")

        accessors = document.get("accessors", [])
        meshes = document.get("meshes", [])
        primitives = vertices = triangles = 0
        mins, maxs = [], []

        for mesh in meshes:
            for primitive in mesh.get("primitives", []):
                primitives += 1
                position_index = primitive.get("attributes", {}).get("POSITION")

                if position_index is not None:
                    accessor = accessors[position_index]
                    vertices += int(accessor.get("count", 0))
                    if "min" in accessor and "max" in accessor:
                        mins.append([float(v) for v in accessor["min"][:3]])
                        maxs.append([float(v) for v in accessor["max"][:3]])

                if int(primitive.get("mode", 4)) == 4:
                    index_accessor = primitive.get("indices")
                    if index_accessor is not None:
                        triangles += int(accessors[index_accessor].get("count", 0)) // 3
                    elif position_index is not None:
                        triangles += int(accessors[position_index].get("count", 0)) // 3

        xyz = [None, None, None]
        if mins:
            lower = [min(item[i] for item in mins) for i in range(3)]
            upper = [max(item[i] for item in maxs) for i in range(3)]
            xyz = [upper[i] - lower[i] for i in range(3)]

        ordered = sorted((v for v in xyz if v is not None), reverse=True)
        ordered += [None] * (3 - len(ordered))

        return {
            "glb_parse_status": "ok",
            "mesh_count": len(meshes),
            "primitive_count": primitives,
            "vertex_count": vertices,
            "triangle_count": triangles,
            "material_count": len(document.get("materials", [])),
            "texture_count": len(document.get("textures", [])),
            "bbox_x_units": xyz[0],
            "bbox_y_units": xyz[1],
            "bbox_z_units": xyz[2],
            "bbox_longest_units": ordered[0],
            "bbox_middle_units": ordered[1],
            "bbox_shortest_units": ordered[2],
        }
    except Exception as error:
        empty["glb_parse_status"] = f"error: {error}"
        return empty


def enrich(source: dict[str, str], models_root: Path, generated_at: str) -> dict[str, Any]:
    row: dict[str, Any] = dict(source)
    row["year_ce"] = number(source.get("year_ce"), int)
    row["is_archaeological_shipwreck"] = flag(source.get("is_archaeological_shipwreck"))

    for field in ("target_length_m", "target_width_m", "target_height_m"):
        row[field] = number(source.get(field), float)

    paths = {
        "glb": source["glb_path"],
        "fbx": source["fbx_path"],
        "reference_image": source["reference_image_path"],
    }
    for role, relative_path in paths.items():
        stats = file_stats(models_root / relative_path)
        for key, value in stats.items():
            row[f"{role}_{key}"] = value

    row.update(glb_stats(models_root / source["glb_path"]))

    longest = row["bbox_longest_units"]
    target_length = row["target_length_m"]
    scale = target_length / longest if target_length and longest and longest > 0 else None

    row["recommended_uniform_scale"] = scale
    row["scaled_length_m"] = target_length if scale else None
    row["scaled_width_m"] = row["bbox_middle_units"] * scale if scale and row["bbox_middle_units"] else None
    row["scaled_height_m"] = row["bbox_shortest_units"] * scale if scale and row["bbox_shortest_units"] else None
    row["all_required_files_present"] = all(row[f"{role}_exists"] for role in paths)
    row["simulation_ready"] = all(
        flag(source.get(item))
        for item in ("orientation_reviewed", "scale_reviewed", "mesh_cleaned", "collision_ready")
    )
    row["orientation_convention"] = "+X forward, +Y left/width, +Z up"
    row["generated_at_utc"] = generated_at
    return row


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)

    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: list[dict[str, Any]], path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "database_name": "Korean Shipwreck 3D Model Database",
                "record_count": len(rows),
                "generated_at_utc": rows[0]["generated_at_utc"] if rows else None,
                "records": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_database(rows: list[dict[str, Any]], path: Path, schema: Path) -> None:
    if path.exists():
        path.unlink()

    connection = sqlite3.connect(path)
    try:
        connection.executescript(schema.read_text(encoding="utf-8"))
        added_ships: set[str] = set()

        for row in rows:
            if row["ship_id"] not in added_ships:
                connection.execute(
                    "INSERT INTO ships VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        row["ship_id"], row["ship_name_ko"], row["ship_name_en"],
                        row["asset_category"], int(row["is_archaeological_shipwreck"]),
                        row["period"] or None, row["year_ce"], row["site_location"] or None,
                        row["site_depth_m"] or None, row["research_summary"] or None,
                    ),
                )
                added_ships.add(row["ship_id"])

            connection.execute(
                """
                INSERT INTO models VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    row["model_id"], row["ship_id"], row["variant"],
                    row["generation_method"], row["generation_tool"],
                    row["target_measurement_type"], row["target_length_m"],
                    row["target_width_m"], row["target_height_m"],
                    row["bbox_x_units"], row["bbox_y_units"], row["bbox_z_units"],
                    row["bbox_longest_units"], row["bbox_middle_units"],
                    row["bbox_shortest_units"], row["recommended_uniform_scale"],
                    row["scaled_length_m"], row["scaled_width_m"], row["scaled_height_m"],
                    row["vertex_count"], row["triangle_count"], row["mesh_count"],
                    row["primitive_count"], row["material_count"], row["texture_count"],
                    int(flag(row["orientation_reviewed"])), int(flag(row["scale_reviewed"])),
                    int(flag(row["mesh_cleaned"])), int(flag(row["collision_ready"])),
                    row["glb_parse_status"] if row["all_required_files_present"] else "missing_required_files",
                    row["notes"] or None,
                ),
            )

            for role, field in (
                ("glb", "glb_path"),
                ("fbx", "fbx_path"),
                ("reference_image", "reference_image_path"),
            ):
                relative_path = row[field]
                connection.execute(
                    "INSERT INTO files (model_id, file_role, relative_path, extension, exists_on_disk, size_bytes, size_mib, sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        row["model_id"], role, relative_path, Path(relative_path).suffix.lower(),
                        int(row[f"{role}_exists"]), row[f"{role}_size_bytes"],
                        row[f"{role}_size_mib"], row[f"{role}_sha256"],
                    ),
                )

            for source_role, field in (
                ("primary", "primary_source_url"),
                ("secondary", "secondary_source_url"),
            ):
                if row[field]:
                    connection.execute(
                        "INSERT INTO sources (model_id, source_role, url, organization, license_note) VALUES (?, ?, ?, ?, ?)",
                        (
                            row["model_id"], source_role, row[field],
                            row["source_organization"], row["license_note"],
                        ),
                    )

        connection.commit()
    finally:
        connection.close()


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--models-root", type=Path, default=here.parent)
    parser.add_argument("--metadata", type=Path, default=here / "source_metadata.csv")
    parser.add_argument("--schema", type=Path, default=here / "schema.sql")
    parser.add_argument("--output-dir", type=Path, default=here / "generated")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    with args.metadata.open("r", newline="", encoding="utf-8-sig") as stream:
        source_rows = list(csv.DictReader(stream))

    model_ids = [row["model_id"] for row in source_rows]
    if len(model_ids) != len(set(model_ids)):
        raise ValueError("model_id values must be unique")

    generated_at = datetime.now(timezone.utc).isoformat()
    rows = [enrich(row, args.models_root.resolve(), generated_at) for row in source_rows]
    missing = [row["model_id"] for row in rows if not row["all_required_files_present"]]

    if args.strict and missing:
        raise FileNotFoundError("Missing files for: " + ", ".join(missing))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(rows, args.output_dir / "shipwreck_catalog.csv")
    write_json(rows, args.output_dir / "shipwreck_catalog.json")
    write_database(rows, args.output_dir / "shipwrecks.sqlite", args.schema)

    print(f"Created {len(rows)} model records in {args.output_dir.resolve()}")
    if missing:
        print("Missing local files for: " + ", ".join(missing))


if __name__ == "__main__":
    main()
