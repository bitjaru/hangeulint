"""HangeuLint: ESLint for Korean AI output."""

__version__ = "0.4.0"

from .analyzer import analyze
from .anchors import compare_anchors, extract_anchors
from .context import load_context_contract, verify_context
from .context_benchmark import (
    build_annotation_package,
    evaluate_context_benchmark,
    load_context_benchmark,
)
from .edit_trace import build_edit_trace
from .rewrite import (
    RewriteCandidate,
    analyze_diversity,
    evaluate_rewrite_candidates,
    load_rewrite_candidate_set,
)

__all__ = [
    "analyze",
    "compare_anchors",
    "extract_anchors",
    "build_edit_trace",
    "build_annotation_package",
    "evaluate_context_benchmark",
    "load_context_contract",
    "load_context_benchmark",
    "verify_context",
    "RewriteCandidate",
    "analyze_diversity",
    "evaluate_rewrite_candidates",
    "load_rewrite_candidate_set",
]
