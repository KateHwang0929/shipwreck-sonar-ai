"""Step 1: make fake sonar data.

This file is the beginner-friendly entry point.
It calls the internal toy simulator code in src/.
"""

from pathlib import Path

from src.toy_simulator.generate_dataset import generate_dataset


if __name__ == "__main__":
    generate_dataset(
        num=200,
        size=256,
        out_dir=Path("data/toy_sim"),
        seed=42,
    )
