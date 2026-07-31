"""HangeuLint: ESLint for Korean AI output."""

__version__ = "0.1.0"

from .analyzer import analyze
from .anchors import compare_anchors, extract_anchors

__all__ = ["analyze", "compare_anchors", "extract_anchors"]
