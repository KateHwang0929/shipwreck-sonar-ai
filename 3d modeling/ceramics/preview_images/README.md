# Ceramic 3D outputs

This directory is the output target for the Mado ceramic multi-view generation pipelines.

For each image group in `../original_models`, the Hunyuan3D Colab generator writes:

- `<group>.glb`, the direct Hunyuan3D mesh
- `<group>.fbx`, the Blender-converted FBX model
- `<group>_preview.png`, a transparent preview render
- `hunyuan3d_manifest.json`, source filenames, view labels, settings, sizes, and SHA-256 checksums

## Free Colab workflow

1. Open `../Hunyuan3D_Ceramics_Colab.ipynb` in Google Colab.
2. Select a T4 GPU or stronger under **Runtime > Change runtime type**.
3. Run all cells. The default setting processes every Mado ceramic group.
4. Review the previews before pushing the generated assets.
5. To push from Colab, add a fine-grained repository token to Colab Secrets as `GITHUB_TOKEN`, with **Contents: Read and write** access only to this repository.

The numbered views are mapped as `_1=front`, `_2=left`, `_3=back`, and `_4=right`.

## Optional Meshy API workflow

The existing GitHub Actions workflow can also generate assets with Meshy, but it requires a paid Meshy API key stored as the repository secret `MESHY_API_KEY`.
