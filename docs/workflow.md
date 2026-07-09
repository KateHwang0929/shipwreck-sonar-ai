# Workflow

This document explains the order of the project in a clear way.

## Big Picture

The project should not start from a full ocean simulator.

The current order is:

```text
1. Toy 2D simulator
2. U-Net toy segmentation
3. AI4Shipwrecks real-data baseline
4. Synthetic + real comparison
5. Korean shipwreck adaptation
6. HoloOcean / Stonefish review
```

## Stage 1: Toy 2D Simulator

Purpose:

```text
Create fake sonar-like images and automatic masks.
```

This stage checks whether the image-to-mask pipeline works.

Input to model:

```text
synthetic sonar-like grayscale image
```

Target label:

```text
binary shipwreck mask
```

The shadow is not labeled as shipwreck.

## Stage 2: U-Net on Toy Data

Purpose:

```text
Check whether a simple segmentation model can learn from the toy data.
```

Output to inspect:

```text
image | ground-truth mask | probability map | predicted mask
```

If the model cannot learn the toy task, do not move to AI4Shipwrecks yet.

## Stage 3: Make Simulation Harder

Add these only after the basic toy pipeline works:

```text
rocks
fishing gear
pottery scatter
background-only images
weaker contrast
more blur
partial burial
stronger seabed texture
```

Purpose:

```text
Test false positives and Korean-style difficulty.
```

## Stage 4: AI4Shipwrecks

AI4Shipwrecks is not the simulator.

It is the real side-scan sonar benchmark.

Purpose:

```text
Train and evaluate the same U-Net pipeline on real SSS image-mask pairs.
```

Experiments:

```text
A. Train toy → test toy
B. Train AI4Shipwrecks → test AI4Shipwrecks
C. Pretrain toy → fine-tune AI4Shipwrecks → test AI4Shipwrecks
```

## Stage 5: Korean Adaptation

After AI4Shipwrecks works, ask:

```text
Why would this fail on Korean wooden shipwrecks?
```

Likely issues:

```text
wooden wrecks have weaker contrast
mudflat and sediment cover objects
shallow water creates noise
rocks and fishing gear create false positives
real expert labels are limited
```

## Stage 6: Bigger Simulators

HoloOcean and Stonefish are for later.

Use them only after the toy simulation and AI4Shipwrecks baseline are clear.

Main question:

```text
Can this simulator generate side-scan-sonar-like images and labels useful for AI training?
```
