# HoloOcean custom-world handoff

The Python pipeline can build the research database and randomized scenario manifest immediately. Rendering requires a packaged HoloOcean world containing the FBX assets.

## Minimum viable version

1. Use the Unreal Engine version required by the HoloOcean version you install.
2. Create a HoloOcean world named `KoreanWreckWorld` in a package named `KoreanWrecks`.
3. Import one FBX first, preferably `3d modeling/완도선/완도선 잔존선체.fbx`.
4. Correct scale and orientation before packaging. The project convention is meters, `+x` forward, `+y` left, and `+z` up.
5. Add valid collision geometry. Raycast sonar depends on collision hits.
6. Place the water surface at `z = 0` and the wreck below it.
7. Configure the wreck as semantic class `shipwreck` so the semantic camera produces a ground-truth mask.
8. Package and install the custom world.
9. Run one dry scene, then one real scene, before starting a large batch.

## Full automation command

For one-world, many-model automation, import all wrecks and assign the actor names listed in `model_registry.csv`. Add a custom HoloOcean world command named `ConfigureShipwreckScene`.

The Python runner sends the active actor name as `string_params[0]` and these numeric parameters:

```text
0  wreck x position in meters
1  wreck y position in meters
2  wreck z position in meters
3  wreck roll in degrees
4  wreck pitch in degrees
5  wreck yaw in degrees
6  sediment burial fraction, 0 to 1
7  visibility in meters
8  turbidity, normalized 0 to 1
9  current speed in meters per second
```

The Unreal implementation should:

1. Hide or disable collision for all inactive wreck actors.
2. Activate the selected wreck actor.
3. Apply the requested location and rotation.
4. Apply burial by changing vertical placement or the sediment system.
5. Update underwater fog or material parameters for visibility and turbidity.
6. Update the current field if the world models water currents.
7. Preserve the `shipwreck` semantic label and collision settings.

After implementing and packaging the command, edit `config.json`:

```json
"world_command": {
  "enabled": true,
  "name": "ConfigureShipwreckScene"
}
```

A nonexistent world command can terminate the HoloOcean environment, so leave it disabled until the Unreal implementation is packaged and tested.

## Recommended validation order

```text
one FBX
-> one packaged world
-> one RGB frame
-> one semantic mask
-> one sonar array
-> one metadata file
-> 10 randomized scenes
-> 100 scenes
-> all registered FBX assets
```
