#!/usr/bin/env python3
"""Generate multiview Mado ceramic models with Tencent Hunyuan3D-2mv."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import torch
from PIL import Image

VIEW_ORDER = ("front", "left", "back", "right")
NAME_PATTERN = re.compile(r"^(mado\d+-\d+)_(\d+)\.(png|jpe?g)$", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--groups", default="all", help="all or comma-separated group names")
    parser.add_argument("--steps", type=int, default=35)
    parser.add_argument("--octree", type=int, default=300)
    parser.add_argument("--chunks", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def discover(input_dir: Path) -> dict[str, list[Path]]:
    grouped: dict[str, list[tuple[int, Path]]] = defaultdict(list)
    for path in input_dir.iterdir():
        match = NAME_PATTERN.match(path.name) if path.is_file() else None
        if match:
            grouped[match.group(1).lower()].append((int(match.group(2)), path))
    result = {
        name: [path for _, path in sorted(items)]
        for name, items in sorted(grouped.items())
    }
    invalid = {name: len(paths) for name, paths in result.items() if not 1 <= len(paths) <= 4}
    if invalid:
        raise ValueError(f"Each ceramic group must have 1-4 views: {invalid}")
    return result


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def blender_script(path: Path) -> None:
    path.write_text(
        r'''
import bpy
import sys
from mathutils import Vector
from pathlib import Path

glb, fbx, preview = map(Path, sys.argv[sys.argv.index("--") + 1:])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not meshes:
    raise RuntimeError("No mesh found in " + str(glb))

points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
center = (low + high) / 2
largest = max(high[i] - low[i] for i in range(3))
scale = 2.0 / largest if largest else 1.0

for obj in meshes:
    obj.location = (obj.location - center) * scale
    obj.scale = tuple(value * scale for value in obj.scale)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True

bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
target = bpy.context.object
bpy.ops.object.camera_add(location=(3.2, -3.2, 2.4))
camera = bpy.context.object
camera.data.lens = 52
constraint = camera.constraints.new(type="TRACK_TO")
constraint.target = target
constraint.track_axis = "TRACK_NEGATIVE_Z"
constraint.up_axis = "UP_Y"
bpy.context.scene.camera = camera

for location, energy, size in [
    ((4, -4, 5), 900, 4.0),
    ((-4, -1, 3), 650, 3.0),
    ((0, 4, 4), 500, 3.0),
]:
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.data.energy = energy
    light.data.size = size
    aim = light.constraints.new(type="TRACK_TO")
    aim.target = target
    aim.track_axis = "TRACK_NEGATIVE_Z"
    aim.up_axis = "UP_Y"

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 768
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.film_transparency = True
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(preview)

bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.export_scene.fbx(
    filepath=str(fbx),
    use_selection=True,
    apply_unit_scale=True,
    path_mode="COPY",
    embed_textures=True,
)
bpy.ops.render.render(write_still=True)
''',
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    source = root / "3d modeling/ceramics/original_models"
    output = root / "3d modeling/ceramics/preview_images"
    hunyuan = Path("/content/Hunyuan3D-2")
    if not source.is_dir():
        raise FileNotFoundError(source)
    if not hunyuan.is_dir():
        raise FileNotFoundError("Clone Tencent-Hunyuan/Hunyuan3D-2 to /content/Hunyuan3D-2 first")
    output.mkdir(parents=True, exist_ok=True)

    groups = discover(source)
    if args.groups.lower() != "all":
        requested = {value.strip().lower() for value in args.groups.split(",") if value.strip()}
        missing = requested - groups.keys()
        if missing:
            raise ValueError(f"Unknown groups: {sorted(missing)}")
        groups = {name: paths for name, paths in groups.items() if name in requested}
    if not groups:
        raise RuntimeError("No Mado ceramic image groups found")

    sys.path.insert(0, str(hunyuan))
    from hy3dgen.rembg import BackgroundRemover
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA GPU is required")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        "tencent/Hunyuan3D-2mv",
        subfolder="hunyuan3d-dit-v2-mv",
        variant="fp16",
    )
    remover = BackgroundRemover()
    converter = Path("/content/hunyuan_glb_to_fbx.py")
    blender_script(converter)

    settings = {
        "groups": args.groups,
        "steps": args.steps,
        "octree": args.octree,
        "chunks": args.chunks,
        "seed": args.seed,
        "overwrite": args.overwrite,
        "repo_root": str(root),
        "view_order": list(VIEW_ORDER),
    }
    manifest = {
        "generator": "Tencent-Hunyuan/Hunyuan3D-2mv",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": settings,
        "models": {},
        "failures": {},
    }

    for index, (name, paths) in enumerate(groups.items(), 1):
        glb = output / f"{name}.glb"
        fbx = output / f"{name}.fbx"
        preview = output / f"{name}_preview.png"
        print(f"\n[{index}/{len(groups)}] {name}: {[p.name for p in paths]}")
        if fbx.exists() and preview.exists() and not args.overwrite:
            print("Skipping existing FBX and preview")
        else:
            try:
                views = {}
                for label, path in zip(VIEW_ORDER, paths):
                    image = Image.open(path).convert("RGBA")
                    if image.getchannel("A").getextrema() == (255, 255):
                        image = remover(image.convert("RGB"))
                    views[label] = image

                started = time.time()
                mesh = pipeline(
                    image=views,
                    num_inference_steps=args.steps,
                    octree_resolution=args.octree,
                    num_chunks=args.chunks,
                    generator=torch.manual_seed(args.seed),
                    output_type="trimesh",
                )[0]
                mesh.export(glb)
                subprocess.run(
                    [
                        "blender",
                        "--background",
                        "--python",
                        str(converter),
                        "--",
                        str(glb),
                        str(fbx),
                        str(preview),
                    ],
                    check=True,
                )
                print(f"Saved {fbx.name} in {time.time() - started:.1f}s")
            except Exception as exc:
                manifest["failures"][name] = f"{type(exc).__name__}: {exc}"
                print(f"ERROR: {exc}", file=sys.stderr)
            finally:
                if "mesh" in locals():
                    del mesh
                torch.cuda.empty_cache()
                gc.collect()

        entry = {
            "source_images": [p.name for p in paths],
            "view_labels": list(VIEW_ORDER[: len(paths)]),
        }
        for key, path in (("glb", glb), ("fbx", fbx), ("preview", preview)):
            if path.exists():
                entry[key] = {
                    "file": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": checksum(path),
                }
        manifest["models"][name] = entry

    (output / "hunyuan3d_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print("\nFinished. Outputs:", output)
    return 1 if manifest["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
