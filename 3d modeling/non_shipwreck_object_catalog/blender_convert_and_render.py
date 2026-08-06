"Convert downloaded Sketchfab glTF/GLB models to FBX and render previews."

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

# Blender intentionally ignores PYTHONPATH unless --python-use-system-env is used.
# Keep this explicit fallback so the script still sees CI-installed dependencies.
extra_python_path = os.environ.get("BLENDER_EXTRA_PYTHONPATH", "")
for entry in reversed([item for item in extra_python_path.split(os.pathsep) if item]):
    if entry not in sys.path:
        sys.path.insert(0, entry)

try:
    import numpy as np
except ModuleNotFoundError as error:
    raise RuntimeError(
        "NumPy is unavailable inside Blender. Run Blender with "
        "--python-use-system-env and set BLENDER_EXTRA_PYTHONPATH."
    ) from error

import bpy
from mathutils import Vector


def script_args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def clear_scene() -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.armatures,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.textures,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def locate_scene(repo_root: Path, category: str, uid: str) -> Path:
    base = (
        repo_root
        / "3d modeling"
        / "non_shipwreck_object_catalog"
        / "downloads"
        / category
        / uid
    )
    marker = base / "scene_path.txt"
    if marker.exists():
        path = Path(marker.read_text(encoding="utf-8").strip())
        if path.exists():
            return path
    for pattern in ("*.glb", "*.gltf"):
        matches = sorted(base.rglob(pattern))
        if matches:
            return matches[0]
    raise FileNotFoundError(f"No downloaded scene for {category}: {base}")


def import_scene(path: Path) -> list[bpy.types.Object]:
    result = bpy.ops.import_scene.gltf(filepath=str(path))
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender did not finish importing {path}")

    meshes = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.data is not None
    ]
    if not meshes:
        raise ValueError(f"No mesh objects imported from {path}")
    return meshes


def make_meshes_world_space(meshes: list[bpy.types.Object]) -> None:
    for obj in meshes:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_render = False
        world_matrix = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world_matrix


def join_meshes(meshes: list[bpy.types.Object], name: str) -> bpy.types.Object:
    make_meshes_world_space(meshes)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]

    if len(meshes) > 1:
        result = bpy.ops.object.join()
        if "FINISHED" not in result:
            raise RuntimeError(f"Blender could not join meshes for {name}")

    joined = bpy.context.view_layer.objects.active
    if joined is None or joined.type != "MESH":
        raise RuntimeError(f"No active joined mesh for {name}")

    joined.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Remove imported cameras, lights, empties, and armatures so they cannot
    # affect the preview or be accidentally exported.
    for candidate in list(bpy.context.scene.objects):
        if candidate != joined:
            bpy.data.objects.remove(candidate, do_unlink=True)

    return joined


def bounds_world(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector(
        (
            min(value.x for value in corners),
            min(value.y for value in corners),
            min(value.z for value in corners),
        )
    )
    maximum = Vector(
        (
            max(value.x for value in corners),
            max(value.y for value in corners),
            max(value.z for value in corners),
        )
    )
    return minimum, maximum


def center_object(obj: bpy.types.Object) -> tuple[Vector, float]:
    minimum, maximum = bounds_world(obj)
    center = (minimum + maximum) / 2
    obj.location -= center
    bpy.context.view_layer.update()

    minimum, maximum = bounds_world(obj)
    extent = maximum - minimum
    if min(extent.x, extent.y, extent.z) < 0:
        raise RuntimeError("Invalid negative object bounds")
    radius = max(extent.length / 2, 0.01)
    return extent, radius


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    if direction.length == 0:
        raise ValueError("Cannot aim an object from the target position")
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera_and_lights(radius: float) -> bpy.types.Object:
    bpy.ops.object.camera_add(
        location=(radius * 2.4, -radius * 2.4, radius * 1.8)
    )
    camera = bpy.context.object
    camera.data.lens = 52
    camera.data.sensor_width = 36
    camera.data.clip_start = max(radius * 0.001, 0.001)
    camera.data.clip_end = max(radius * 25, 1000)
    point_at(camera, Vector((0, 0, 0)))
    bpy.context.scene.camera = camera

    light_positions = (
        (radius * 2.5, -radius * 1.5, radius * 3.0, 1100),
        (-radius * 2.0, -radius * 0.5, radius * 1.5, 750),
        (0, radius * 2.0, radius * 2.0, 600),
    )
    for x, y, z, energy in light_positions:
        bpy.ops.object.light_add(type="AREA", location=(x, y, z))
        light = bpy.context.object
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = max(radius * 1.8, 0.5)
        point_at(light, Vector((0, 0, 0)))
    return camera


def select_render_engine() -> str:
    scene = bpy.context.scene
    failures: list[str] = []
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            return engine
        except (TypeError, ValueError) as error:
            failures.append(f"{engine}: {error}")
    raise RuntimeError("No supported render engine: " + "; ".join(failures))


def configure_render(output: Path) -> str:
    scene = bpy.context.scene
    engine = select_render_engine()
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = True
    scene.render.filepath = str(output)
    return engine


def export_fbx(obj: bpy.types.Object, output: Path) -> bool:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    common = {
        "filepath": str(output),
        "use_selection": True,
        "object_types": {"MESH"},
        "apply_unit_scale": True,
        "bake_space_transform": False,
        "add_leaf_bones": False,
        "use_mesh_modifiers": True,
    }

    embedded = True
    try:
        result = bpy.ops.export_scene.fbx(
            **common,
            path_mode="COPY",
            embed_textures=True,
        )
    except Exception as error:
        embedded = False
        print(
            f"[warning] Embedded-texture FBX export failed: {error}. "
            "Retrying without embedded textures.",
            file=sys.stderr,
        )
        result = bpy.ops.export_scene.fbx(
            **common,
            path_mode="AUTO",
            embed_textures=False,
        )

    if "FINISHED" not in result:
        raise RuntimeError(f"Blender did not finish exporting {output}")
    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError(f"FBX export is missing or empty: {output}")
    return embedded


def render_preview(output: Path, preferred_engine: str) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    engines = [preferred_engine]
    for fallback in ("BLENDER_WORKBENCH", "CYCLES"):
        if fallback not in engines:
            engines.append(fallback)

    failures: list[str] = []
    for engine in engines:
        try:
            scene.render.engine = engine
            if engine == "CYCLES":
                scene.cycles.device = "CPU"
                scene.cycles.samples = 16
            result = bpy.ops.render.render(write_still=True)
            if "FINISHED" not in result:
                raise RuntimeError(f"render returned {sorted(result)}")
            if not output.is_file() or output.stat().st_size < 256:
                raise RuntimeError("rendered file is missing or empty")
            return engine
        except Exception as error:
            failures.append(f"{engine}: {error}")
            print(
                f"[warning] Preview render failed with {engine}: {error}",
                file=sys.stderr,
            )

    raise RuntimeError("All preview render engines failed: " + "; ".join(failures))


def main() -> int:
    print(
        f"Blender {bpy.app.version_string}; Python {sys.version.split()[0]}; "
        f"NumPy {np.__version__}"
    )

    args = script_args()
    repo_root = args.repo_root.resolve()
    catalog = args.catalog
    if not catalog.is_absolute():
        catalog = (repo_root / catalog).resolve()

    with catalog.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))

    selected = set(args.category)
    if selected:
        rows = [row for row in rows if row["category"] in selected]

    report_path = (
        repo_root
        / "3d modeling"
        / "non_shipwreck_object_catalog"
        / "validation_report.csv"
    )
    report_rows: list[dict[str, str | int]] = []

    for row in rows:
        category = row["category"]
        uid = row["sketchfab_uid"]
        target_fbx = repo_root / row["target_fbx"]
        target_preview = repo_root / row["target_preview"]

        if not args.overwrite and target_fbx.exists() and target_preview.exists():
            print(f"[skip] {category}")
            report_rows.append(
                {
                    "category": category,
                    "status": "ok",
                    "mesh_nodes_before_join": "",
                    "materials_after_join": "",
                    "extent_x": "",
                    "extent_y": "",
                    "extent_z": "",
                    "fbx": str(target_fbx.relative_to(repo_root)),
                    "preview": str(target_preview.relative_to(repo_root)),
                    "textures_embedded": "",
                    "render_engine": "",
                    "error": "",
                }
            )
            continue

        try:
            clear_scene()
            scene_path = locate_scene(repo_root, category, uid)
            meshes = import_scene(scene_path)
            mesh_count = len(meshes)
            obj = join_meshes(meshes, category)
            extent, radius = center_object(obj)

            material_count = len(obj.data.materials)
            setup_camera_and_lights(radius)
            preferred_engine = configure_render(target_preview)
            textures_embedded = export_fbx(obj, target_fbx)
            engine = render_preview(target_preview, preferred_engine)

            report_rows.append(
                {
                    "category": category,
                    "status": "ok" if material_count == 1 else "review_materials",
                    "mesh_nodes_before_join": mesh_count,
                    "materials_after_join": material_count,
                    "extent_x": f"{extent.x:.6g}",
                    "extent_y": f"{extent.y:.6g}",
                    "extent_z": f"{extent.z:.6g}",
                    "fbx": str(target_fbx.relative_to(repo_root)),
                    "preview": str(target_preview.relative_to(repo_root)),
                    "textures_embedded": "yes" if textures_embedded else "no",
                    "render_engine": engine,
                    "error": "",
                }
            )
            print(
                f"[ok] {category}: {target_fbx.name}, "
                f"{target_preview.name}, materials={material_count}, engine={engine}"
            )
        except Exception as error:
            report_rows.append(
                {
                    "category": category,
                    "status": "error",
                    "mesh_nodes_before_join": "",
                    "materials_after_join": "",
                    "extent_x": "",
                    "extent_y": "",
                    "extent_z": "",
                    "fbx": str(target_fbx.relative_to(repo_root)),
                    "preview": str(target_preview.relative_to(repo_root)),
                    "textures_embedded": "",
                    "render_engine": "",
                    "error": str(error),
                }
            )
            print(f"[error] {category}: {error}", file=sys.stderr)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "category",
        "status",
        "mesh_nodes_before_join",
        "materials_after_join",
        "extent_x",
        "extent_y",
        "extent_z",
        "fbx",
        "preview",
        "textures_embedded",
        "render_engine",
        "error",
    ]
    with report_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    failures = [row for row in report_rows if row["status"] == "error"]
    print(f"Wrote {report_path}; failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
