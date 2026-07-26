from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sqlite3
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
NUMERIC_CATALOG_FIELDS = {
    "water_depth_min_m", "water_depth_max_m",
    "remaining_length_m", "remaining_width_m", "remaining_height_m",
    "estimated_length_m", "estimated_width_m", "estimated_height_m",
    "restored_length_m", "restored_width_m", "restored_height_m",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value: str | None) -> float | None:
    value = (value or "").strip()
    return None if not value else float(value)


def as_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def validate(catalog_path: Path, registry_path: Path, config_path: Path) -> None:
    catalog = read_csv(catalog_path)
    registry = read_csv(registry_path)
    config = read_json(config_path)
    wreck_ids = [row["wreck_id"] for row in catalog]
    asset_ids = [row["asset_id"] for row in registry]
    if len(wreck_ids) != len(set(wreck_ids)):
        raise ValueError("Duplicate wreck_id")
    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("Duplicate asset_id")
    known_wrecks = set(wreck_ids)
    unknown = [
        row["wreck_id"]
        for row in registry
        if row["wreck_id"] and row["wreck_id"] not in known_wrecks
    ]
    if unknown:
        raise ValueError(f"Unknown wreck_id values in registry: {unknown}")
    if not all(row["source_url"].startswith("https://") for row in catalog):
        raise ValueError("Every catalog record needs an HTTPS source URL")
    if int(config["num_scenes"]) <= 0:
        raise ValueError("num_scenes must be positive")
    print(f"Catalog records: {len(catalog)}")
    print(f"Registered FBX assets: {len(registry)}")
    print("Validation passed")


def build_database(catalog_path: Path, output_path: Path) -> None:
    rows = read_csv(catalog_path)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = dict(row)
        for field in NUMERIC_CATALOG_FIELDS:
            item[field] = as_float(row[field])
        item["local_asset_available"] = int(as_bool(row["local_asset_available"]))
        normalized.append(item)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    connection = sqlite3.connect(output_path)
    try:
        columns = list(normalized[0])
        types = [
            "REAL" if column in NUMERIC_CATALOG_FIELDS
            else "INTEGER" if column == "local_asset_available"
            else "TEXT"
            for column in columns
        ]
        definitions = ",".join(
            f'"{column}" {kind}' + (" PRIMARY KEY" if column == "wreck_id" else "")
            for column, kind in zip(columns, types)
        )
        connection.execute(f"CREATE TABLE wrecks ({definitions})")
        marks = ",".join("?" for _ in columns)
        names = ",".join(f'"{column}"' for column in columns)
        connection.executemany(
            f"INSERT INTO wrecks ({names}) VALUES ({marks})",
            [[row[column] for column in columns] for row in normalized],
        )
        connection.execute("CREATE INDEX idx_wreck_period ON wrecks(period)")
        connection.execute("CREATE INDEX idx_wreck_asset ON wrecks(local_asset_available)")
        connection.commit()
    finally:
        connection.close()
    print(f"Created {output_path} with {len(normalized)} records")


def sample_range(rng: random.Random, limits: list[float]) -> float:
    return rng.uniform(float(limits[0]), float(limits[1]))


def point_at(
    sensor: list[float],
    target: list[float],
    roll: float,
    pitch_jitter: float,
    yaw_jitter: float,
) -> list[float]:
    dx, dy, dz = (target[i] - sensor[i] for i in range(3))
    yaw = math.degrees(math.atan2(dy, dx)) + yaw_jitter
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy))) + pitch_jitter
    return [round(roll, 5), round(pitch, 5), round(yaw, 5)]


def eligible_assets(
    registry: list[dict[str, str]],
    config: dict[str, Any],
    repo_root: Path,
    allow_missing: bool,
) -> list[dict[str, Any]]:
    asset_filter = config["asset_filter"]
    allowed_status = set(asset_filter.get("simulation_status", []))
    output: list[dict[str, Any]] = []
    for row in registry:
        if asset_filter.get("asset_kind") and row["asset_kind"] != asset_filter["asset_kind"]:
            continue
        if allowed_status and row["simulation_status"] not in allowed_status:
            continue
        exists = (repo_root / row["fbx_path"]).is_file()
        if exists or allow_missing:
            item: dict[str, Any] = dict(row)
            item["fbx_exists"] = exists
            output.append(item)
    if not output:
        raise RuntimeError(
            "No eligible FBX assets. Check --repo-root or use --allow-missing-assets."
        )
    return output


def make_scene(
    index: int,
    asset: dict[str, Any],
    config: dict[str, Any],
    rng: random.Random,
) -> dict[str, Any]:
    sampling = config["sampling"]
    defaults = config["world_defaults"]
    sensor_config = config["sensors"]
    wreck = [
        float(asset.get("wreck_x_m") or defaults["wreck_location_m"][0]),
        float(asset.get("wreck_y_m") or defaults["wreck_location_m"][1]),
        float(asset.get("wreck_z_m") or defaults["wreck_location_m"][2]),
    ]
    radius = sample_range(rng, sampling["sensor_distance_m"])
    angle = sample_range(rng, sampling["orbit_angle_deg"])
    height = sample_range(rng, sampling["sensor_height_above_wreck_m"])
    angle_rad = math.radians(angle)
    location = [
        wreck[0] + radius * math.cos(angle_rad),
        wreck[1] + radius * math.sin(angle_rad),
        wreck[2] + height,
    ]
    rotation = point_at(
        location,
        wreck,
        sample_range(rng, sampling["sensor_roll_deg"]),
        sample_range(rng, sampling["sensor_pitch_jitter_deg"]),
        sample_range(rng, sampling["sensor_yaw_jitter_deg"]),
    )
    return {
        "scene_id": f"scene_{index:06d}",
        "asset": {
            "asset_id": asset["asset_id"],
            "wreck_id": asset["wreck_id"] or None,
            "name_ko": asset["name_ko"],
            "variant": asset["variant"],
            "fbx_path": asset["fbx_path"],
            "fbx_exists": bool(asset["fbx_exists"]),
            "unreal_actor_name": asset["unreal_actor_name"],
            "semantic_label": asset["semantic_label"],
        },
        "world": {
            "package_name": asset.get("unreal_package_name") or defaults["package_name"],
            "world_name": asset.get("unreal_world_name") or defaults["world_name"],
            "wreck_location_m": [round(value, 5) for value in wreck],
            "wreck_rotation_rpy_deg": [
                round(sample_range(rng, sampling["wreck_roll_deg"]), 5),
                round(sample_range(rng, sampling["wreck_pitch_deg"]), 5),
                round(sample_range(rng, sampling["wreck_yaw_deg"]), 5),
            ],
            "visibility_m": round(sample_range(rng, sampling["visibility_m"]), 5),
            "turbidity": round(sample_range(rng, sampling["turbidity"]), 5),
            "current_speed_mps": round(
                sample_range(rng, sampling["current_speed_mps"]), 5
            ),
            "sediment_burial_fraction": round(
                sample_range(rng, sampling["sediment_burial_fraction"]), 5
            ),
        },
        "agent": {
            "name": "auv0",
            "type": "HoveringAUV",
            "location_m": [round(value, 5) for value in location],
            "rotation_rpy_deg": rotation,
            "distance_to_wreck_m": round(radius, 5),
            "height_above_wreck_m": round(height, 5),
        },
        "sensors": {
            "capture_width": int(sensor_config["capture_width"]),
            "capture_height": int(sensor_config["capture_height"]),
            "hz": int(sensor_config["hz"]),
            "sonar": {
                "range_bins": int(sensor_config["range_bins"]),
                "azimuth_bins": int(sensor_config["azimuth_bins"]),
                "azimuth_ray_count": int(sensor_config["azimuth_ray_count"]),
                "elevation_ray_count": int(sensor_config["elevation_ray_count"]),
                "range_min_m": 0.5,
                "range_max_m": round(
                    sample_range(rng, sampling["sonar_range_max_m"]), 5
                ),
                "azimuth_deg": round(
                    sample_range(rng, sampling["sonar_azimuth_deg"]), 5
                ),
                "elevation_deg": round(
                    sample_range(rng, sampling["sonar_elevation_deg"]), 5
                ),
                "add_sigma": round(
                    sample_range(rng, sampling["sonar_add_sigma"]), 6
                ),
                "mult_sigma": round(
                    sample_range(rng, sampling["sonar_mult_sigma"]), 6
                ),
            },
        },
    }


def generate_manifest(
    registry_path: Path,
    config_path: Path,
    repo_root: Path,
    output: Path,
    count: int | None,
    seed: int | None,
    allow_missing: bool,
) -> None:
    config = read_json(config_path)
    if count is not None:
        config["num_scenes"] = count
    if seed is not None:
        config["seed"] = seed
    rng = random.Random(int(config["seed"]))
    assets = eligible_assets(
        read_csv(registry_path), config, repo_root, allow_missing
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        for index in range(int(config["num_scenes"])):
            scene = make_scene(index, rng.choice(assets), config, rng)
            stream.write(json.dumps(scene, ensure_ascii=False) + "\n")
    print(
        f"Created {output} with {config['num_scenes']} scenes from {len(assets)} assets"
    )


def make_scenario(scene: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    agent = scene["agent"]
    sensors = scene["sensors"]
    sonar = sensors["sonar"]
    hz = sensors["hz"]
    width = sensors["capture_width"]
    height = sensors["capture_height"]
    return {
        "name": scene["scene_id"],
        "world": scene["world"]["world_name"],
        "package_name": scene["world"]["package_name"],
        "main_agent": agent["name"],
        "ticks_per_sec": config["runner"]["ticks_per_sec"],
        "frames_per_sec": config["runner"]["frames_per_sec"],
        "agents": [
            {
                "agent_name": agent["name"],
                "agent_type": agent["type"],
                "control_scheme": 0,
                "location": agent["location_m"],
                "rotation": agent["rotation_rpy_deg"],
                "sensors": [
                    {
                        "sensor_type": "RGBCamera",
                        "sensor_name": "RGB",
                        "socket": "CameraSocket",
                        "Hz": hz,
                        "configuration": {
                            "CaptureWidth": width,
                            "CaptureHeight": height,
                        },
                    },
                    {
                        "sensor_type": "DepthCamera",
                        "sensor_name": "Depth",
                        "socket": "CameraSocket",
                        "Hz": hz,
                        "configuration": {
                            "CaptureWidth": width,
                            "CaptureHeight": height,
                        },
                    },
                    {
                        "sensor_type": "SemanticSegmentationCamera",
                        "sensor_name": "Semantic",
                        "socket": "CameraSocket",
                        "Hz": hz,
                        "configuration": {
                            "CaptureWidth": width,
                            "CaptureHeight": height,
                        },
                    },
                    {
                        "sensor_type": "RaycastImagingSonar",
                        "sensor_name": "Sonar",
                        "socket": "SonarSocket",
                        "Hz": hz,
                        "configuration": {
                            "RangeBins": sonar["range_bins"],
                            "AzimuthBins": sonar["azimuth_bins"],
                            "AzimuthRayCount": sonar["azimuth_ray_count"],
                            "ElevationRayCount": sonar["elevation_ray_count"],
                            "RangeMin": sonar["range_min_m"],
                            "RangeMax": sonar["range_max_m"],
                            "Elevation": sonar["elevation_deg"],
                            "Azimuth": sonar["azimuth_deg"],
                            "MultSigma": sonar["mult_sigma"],
                            "AddSigma": sonar["add_sigma"],
                            "MultiPath": False,
                            "ViewRegion": False,
                            "WaterDensity": 997,
                            "WaterSpeedSound": 1480,
                            "IgnorePlants": False,
                        },
                    },
                    {
                        "sensor_type": "PoseSensor",
                        "sensor_name": "Pose",
                    },
                ],
            }
        ],
    }


def manifest_rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at line {line_number}") from error


def save_array_outputs(
    state: dict[str, Any],
    scene_dir: Path,
    scene: dict[str, Any],
    scenario: dict[str, Any],
) -> None:
    import numpy as np
    from PIL import Image

    scene_dir.mkdir(parents=True, exist_ok=True)
    if "RGB" in state:
        rgb = np.asarray(state["RGB"])[:, :, :3].astype(np.uint8)
        Image.fromarray(rgb).save(scene_dir / "rgb.png")
    if "Semantic" in state:
        semantic = np.asarray(state["Semantic"])[:, :, :3].astype(np.uint8)
        Image.fromarray(semantic).save(scene_dir / "semantic.png")
    if "Depth" in state:
        np.save(scene_dir / "depth.npy", np.asarray(state["Depth"]))
    if "Pose" in state:
        np.save(scene_dir / "pose.npy", np.asarray(state["Pose"]))
    if "Sonar" in state:
        sonar = np.asarray(state["Sonar"], dtype=np.float32)
        np.save(scene_dir / "sonar.npy", sonar)
        finite = sonar[np.isfinite(sonar)]
        low, high = np.percentile(finite, [1, 99]) if finite.size else (0.0, 1.0)
        if high <= low:
            high = low + 1.0
        preview = (
            np.clip((sonar - low) / (high - low), 0, 1) * 255
        ).astype(np.uint8)
        Image.fromarray(preview).save(scene_dir / "sonar_preview.png")
    metadata = dict(scene)
    metadata["scenario"] = scenario
    metadata["captured_sensor_keys"] = sorted(state)
    (scene_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_manifest(
    manifest: Path,
    config_path: Path,
    output: Path,
    limit: int | None,
    dry_run: bool,
    resume: bool,
) -> None:
    config = read_json(config_path)
    if not dry_run:
        try:
            import holoocean
        except ImportError as error:
            raise RuntimeError("Install HoloOcean or use --dry-run") from error

    completed = 0
    for index, scene in enumerate(manifest_rows(manifest)):
        if limit is not None and index >= limit:
            break
        scene_dir = output / scene["scene_id"]
        if resume and (scene_dir / "metadata.json").exists():
            continue
        scenario = make_scenario(scene, config)
        scene_dir.mkdir(parents=True, exist_ok=True)

        if dry_run:
            (scene_dir / "scenario.json").write_text(
                json.dumps(scenario, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (scene_dir / "metadata.json").write_text(
                json.dumps(scene, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            with holoocean.make(
                scenario_cfg=scenario,
                show_viewport=bool(config["runner"]["show_viewport"]),
            ) as environment:
                command = config["runner"].get("world_command", {})
                if command.get("enabled"):
                    world = scene["world"]
                    environment.send_world_command(
                        command["name"],
                        num_params=[
                            *world["wreck_location_m"],
                            *world["wreck_rotation_rpy_deg"],
                            world["sediment_burial_fraction"],
                            world["visibility_m"],
                            world["turbidity"],
                            world["current_speed_mps"],
                        ],
                        string_params=[scene["asset"]["unreal_actor_name"]],
                    )
                state: dict[str, Any] = {}
                tick_count = int(config["runner"]["warmup_ticks"]) + int(
                    config["runner"]["capture_ticks"]
                )
                for _ in range(tick_count):
                    raw = environment.tick()
                    state = (
                        raw.get(scene["agent"]["name"], raw)
                        if isinstance(raw, dict)
                        else {}
                    )
                if not state:
                    raise RuntimeError(f"No sensor state for {scene['scene_id']}")
                save_array_outputs(state, scene_dir, scene, scenario)
        completed += 1
        print(f"Saved: {scene['scene_id']}")
    print(f"Completed: {completed}")


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        description="Korean shipwreck database and HoloOcean synthetic-data pipeline"
    )
    commands = argument_parser.add_subparsers(dest="command", required=True)

    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument(
        "--catalog", type=Path, default=ROOT / "korean_shipwreck_catalog.csv"
    )
    validate_parser.add_argument(
        "--registry", type=Path, default=ROOT / "model_registry.csv"
    )
    validate_parser.add_argument(
        "--config", type=Path, default=ROOT / "config.json"
    )

    database_parser = commands.add_parser("build-db")
    database_parser.add_argument(
        "--catalog", type=Path, default=ROOT / "korean_shipwreck_catalog.csv"
    )
    database_parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated" / "korean_shipwrecks.sqlite",
    )

    manifest_parser = commands.add_parser("manifest")
    manifest_parser.add_argument(
        "--registry", type=Path, default=ROOT / "model_registry.csv"
    )
    manifest_parser.add_argument(
        "--config", type=Path, default=ROOT / "config.json"
    )
    manifest_parser.add_argument("--repo-root", type=Path, default=ROOT.parent)
    manifest_parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated" / "scene_manifest.jsonl",
    )
    manifest_parser.add_argument("--num-scenes", type=int)
    manifest_parser.add_argument("--seed", type=int)
    manifest_parser.add_argument("--allow-missing-assets", action="store_true")

    run_parser = commands.add_parser("run")
    run_parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "generated" / "scene_manifest.jsonl",
    )
    run_parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    run_parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "generated" / "dataset",
    )
    run_parser.add_argument("--limit", type=int)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--resume", action="store_true")
    return argument_parser


def main() -> None:
    args = parser().parse_args()
    if args.command == "validate":
        validate(args.catalog, args.registry, args.config)
    elif args.command == "build-db":
        build_database(args.catalog, args.output)
    elif args.command == "manifest":
        generate_manifest(
            args.registry,
            args.config,
            args.repo_root.resolve(),
            args.output,
            args.num_scenes,
            args.seed,
            args.allow_missing_assets,
        )
    elif args.command == "run":
        run_manifest(
            args.manifest,
            args.config,
            args.output,
            args.limit,
            args.dry_run,
            args.resume,
        )
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
