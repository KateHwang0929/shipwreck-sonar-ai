"""Dataset loaders for sonar segmentation."""

from .toy_dataset import ToySonarDataset
from .ai4shipwrecks_dataset import AI4ShipwrecksDataset

__all__ = ["ToySonarDataset", "AI4ShipwrecksDataset"]
