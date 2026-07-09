"""Step 3: train the AI model.

This trains a small U-Net model on the fake sonar data.
"""

import subprocess
import sys


if __name__ == "__main__":
    command = [
        sys.executable,
        "src/training/train_unet.py",
        "--data-dir",
        "data/toy_sim",
        "--epochs",
        "5",
        "--batch-size",
        "8",
        "--out-dir",
        "results/toy_unet",
    ]
    subprocess.run(command, check=True)
