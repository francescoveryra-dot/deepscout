from deepscout_evaluation.retrieval_metrics import (
    duplicate_candidate_rate,
    mrr,
    precision_at_k,
    recall_at_k,
)


def test_recall_at_k() -> None:
    assert recall_at_k(relevant_found=2, total_relevant=4, k=3) == 0.5


def test_precision_at_k() -> None:
    assert precision_at_k(relevant_found=2, returned=5, k=3) == 2 / 3


def test_mrr_first_hit() -> None:
    assert mrr(first_relevant_rank=2) == 0.5


def test_duplicate_rate() -> None:
    assert duplicate_candidate_rate(total=4, unique_snapshots=3) == 0.25
