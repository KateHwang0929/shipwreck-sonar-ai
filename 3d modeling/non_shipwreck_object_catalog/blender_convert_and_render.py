"""Convert downloaded Sketchfab glTF/GLB models to FBX and render previews.

Run with:
blender --background --python blender_convert_and_render.py -- \
  --repo-root . --catalog model_catalog.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

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
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)


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
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise ValueError(f"No mesh objects imported from {path}")
    return meshes


def join_meshes(meshes: list[bpy.types.Object], name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return joined


def bounds_world(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
    maximum = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
    return minimum, maximum


def center_object(obj: bpy.types.Object) -> tuple[Vector, float]:
    minimum, maximum = bounds_world(obj)
    center = (minimum + maximum) / 2
    obj.location -= center
    bpy.context.view_layer.update()
    minimum, maximum = bounds_world(obj)
    extent = maximum - minimum
    radius = max(extent.length / 2, 0.001)
    return extent, radius


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera_and_lights(radius: float) -> bpy.types.Object:
    bpy.ops.object.camera_add(location=(radius * 2.2, -radius * 2.2, radius * 1.65))
    camera = bpy.context.object
    camera.data.lens = 55
    camera.data.sensor_width = 36
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


def configure_render(output: Path) -> None:
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.render.filepath = str(output)


def export_fbx(obj: bpy.types.Object, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=str(output),
        use_selection=True,
        apply_unit_scale=True,
        bake_space_transform=False,
        add_leaf_bones=False,
        path_mode="COPY",
        embed_textures=True,
    )


def main() -> int:
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
            target_preview.parent.mkdir(parents=True, exist_ok=True)
            configure_render(target_preview)
            export_fbx(obj, target_fbx)
            bpy.ops.render.render(write_still=True)

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
                    "error": "",
                }
            )
            print(
                f"[ok] {category}: {target_fbx.name}, "
                f"{target_preview.name}, materials={material_count}"
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
        "error",
    ]
    with report_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    return 1 if any(row["status"] == "error" for row in report_rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
