"""Segmentation metrics for binary shipwreck masks."""

from __future__ import annotations

import torch


def dice_score_from_logits(logits: torch.Tensor, targets: torch.Tensor, threshold: float = 0.5, eps: float = 1e-7) -> torch.Tensor:
    """Calculate Dice score from raw model logits."""
    probs = torch.sigmoid(logits)
    preds = (probs >= threshold).float()
    targets = (targets >= 0.5).float()

    dims = tuple(range(1, preds.ndim))
    intersection = (preds * targets).sum(dim=dims)
    denominator = preds.sum(dim=dims) + targets.sum(dim=dims)
    return ((2.0 * intersection + eps) / (denominator + eps)).mean()


def iou_score_from_logits(logits: torch.Tensor, targets: torch.Tensor, threshold: float = 0.5, eps: float = 1e-7) -> torch.Tensor:
    """Calculate IoU score from raw model logits."""
    probs = torch.sigmoid(logits)
    preds = (probs >= threshold).float()
    targets = (targets >= 0.5).float()

    dims = tuple(range(1, preds.ndim))
    intersection = (preds * targets).sum(dim=dims)
    union = preds.sum(dim=dims) + targets.sum(dim=dims) - intersection
    return ((intersection + eps) / (union + eps)).mean()


def precision_from_logits(logits: torch.Tensor, targets: torch.Tensor, threshold: float = 0.5, eps: float = 1e-7) -> torch.Tensor:
    """Calculate pixel-level precision from logits."""
    probs = torch.sigmoid(logits)
    preds = (probs >= threshold).float()
    targets = (targets >= 0.5).float()

    dims = tuple(range(1, preds.ndim))
    true_positive = (preds * targets).sum(dim=dims)
    predicted_positive = preds.sum(dim=dims)
    return ((true_positive + eps) / (predicted_positive + eps)).mean()


def recall_from_logits(logits: torch.Tensor, targets: torch.Tensor, threshold: float = 0.5, eps: float = 1e-7) -> torch.Tensor:
    """Calculate pixel-level recall from logits."""
    probs = torch.sigmoid(logits)
    preds = (probs >= threshold).float()
    targets = (targets >= 0.5).float()

    dims = tuple(range(1, preds.ndim))
    true_positive = (preds * targets).sum(dim=dims)
    actual_positive = targets.sum(dim=dims)
    return ((true_positive + eps) / (actual_positive + eps)).mean()


def dice_loss_from_logits(logits: torch.Tensor, targets: torch.Tensor, eps: float = 1e-7) -> torch.Tensor:
    """Differentiable Dice loss for training."""
    probs = torch.sigmoid(logits)
    targets = (targets >= 0.5).float()

    dims = tuple(range(1, probs.ndim))
    intersection = (probs * targets).sum(dim=dims)
    denominator = probs.sum(dim=dims) + targets.sum(dim=dims)
    dice = (2.0 * intersection + eps) / (denominator + eps)
    return 1.0 - dice.mean()
