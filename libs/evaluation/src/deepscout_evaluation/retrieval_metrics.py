"""Retrieval-specific deterministic metrics."""

from __future__ import annotations


def recall_at_k(*, relevant_found: int, total_relevant: int, k: int) -> float:
    if total_relevant == 0:
        return 0.0
    return min(relevant_found, k) / total_relevant


def precision_at_k(*, relevant_found: int, returned: int, k: int) -> float:
    if returned == 0:
        return 0.0
    return min(relevant_found, k) / min(returned, k)


def mrr(*, first_relevant_rank: int | None) -> float:
    if first_relevant_rank is None or first_relevant_rank <= 0:
        return 0.0
    return 1.0 / first_relevant_rank


def duplicate_candidate_rate(*, total: int, unique_snapshots: int) -> float:
    if total == 0:
        return 0.0
    return 1.0 - (unique_snapshots / total)
