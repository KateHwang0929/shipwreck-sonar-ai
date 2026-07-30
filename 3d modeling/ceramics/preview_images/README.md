# Ceramic FBX outputs

This directory is the output target for the Mado ceramic multi-view generation pipeline.

For each image group in `../original_models`, the generator writes:

- `<group>.fbx`, the textured FBX model
- `<group>_preview.png`, Meshy's preview render
- `meshy_manifest.json`, task IDs, source filenames, file sizes, and SHA-256 checksums

## Generate through GitHub Actions

1. In the repository, open **Settings > Secrets and variables > Actions**.
2. Add a repository secret named `MESHY_API_KEY`.
3. Open **Actions > Generate ceramic FBX with Meshy > Run workflow**.
4. Enter one group such as `mado18-28`, or use `all` for every ceramic set.

The API key is read only from the GitHub Actions secret and is never written to the repository.
