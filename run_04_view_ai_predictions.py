"""Step 4: view AI predictions.

Creates a grid image showing:
sonar image | true mask | AI probability | AI predicted mask
"""

import subprocess
import sys


if __name__ == "__main__":
    command = [
        sys.executable,
        "src/training/visualize_predictions.py",
        "--data-dir",
        "data/toy_sim",
        "--checkpoint",
        "results/toy_unet/best_unet.pt",
        "--num",
        "8",
        "--out",
        "results/toy_unet/predictions_grid.png",
    ]
    subprocess.run(command, check=True)
