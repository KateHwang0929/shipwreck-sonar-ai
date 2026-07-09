"""Step 2: view fake sonar data.

Creates a grid image showing:
sonar-like image | mask | overlay
"""

from pathlib import Path

from src.toy_simulator.visualize_samples import visualize


if __name__ == "__main__":
    visualize(
        data_dir=Path("data/toy_sim"),
        num=8,
        out=Path("results/toy_samples_grid.png"),
    )
