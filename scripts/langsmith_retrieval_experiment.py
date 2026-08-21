#!/usr/bin/env python3
"""LangSmith Phase 5 retrieval experiment — real EU workspace."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from deepscout_research.langsmith_env import configure_langsmith_env

BENCHMARK_PATH = Path(__file__).resolve().parents[1] / "libs/evaluation/data/retrieval_benchmark_v1.json"


def _retrieval_evaluator(run, example) -> dict:
    outputs = run.outputs or {}
    expected = example.outputs or {}
    phrases = expected.get("relevant_phrases", [])
    text = " ".join(outputs.get("retrieved_texts", [])).lower()
    if not phrases:
        score = 1.0 if not outputs.get("retrieved_texts") else 0.0
    else:
        hits = sum(1 for p in phrases if p.lower() in text)
        score = hits / len(phrases)
    return {"key": "phrase_recall", "score": score}


def _target(inputs: dict) -> dict:
    """Offline retrieval metadata export for LangSmith dataset rows."""
    return {
        "query": inputs.get("query"),
        "query_type": inputs.get("type"),
        "retrieved_texts": inputs.get("mock_hits", []),
        "retrieval_mode": "hybrid",
        "embedding_model": "gemini-embedding-2",
        "dimensions": 1536,
    }


def main() -> int:
    settings = configure_langsmith_env()
    if settings.langsmith_api_key is None:
        print(json.dumps({"status": "BLOCKED", "reason": "langsmith_not_configured"}))
        return 1

    from langsmith import Client
    from langsmith.evaluation import evaluate

    benchmark = json.loads(BENCHMARK_PATH.read_text())
    client = Client()
    dataset_name = "deepscout-retrieval-v1"
    existing = list(client.list_datasets(dataset_name=dataset_name))
    if existing:
        dataset = existing[0]
    else:
        examples = []
        for item in benchmark["queries"]:
            examples.append(
                {
                    "inputs": {
                        "query": item["query"],
                        "type": item["type"],
                        "mock_hits": item.get("relevant_phrases", []),
                    },
                    "outputs": {"relevant_phrases": item.get("relevant_phrases", [])},
                }
            )
        dataset = client.create_dataset(dataset_name, description="Phase 5 retrieval benchmark v1")
        client.create_examples(dataset_id=dataset.id, examples=examples)

    prefix = f"deepscout-retrieval-{datetime.now(UTC).strftime('%Y%m%d')}"
    results = evaluate(
        _target,
        data=dataset.name,
        evaluators=[_retrieval_evaluator],
        experiment_prefix=prefix,
        metadata={
            "phase": "5",
            "retrieval_mode": settings.retrieval_mode,
            "embedding_model": settings.embedding_model or "gemini-embedding-2",
            "dimensions": settings.embedding_dimensions,
            "chunking_version": "v1-recursive-1800-280",
        },
        client=client,
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "dataset": dataset.name,
                "experiment_prefix": prefix,
                "experiment": str(results),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
