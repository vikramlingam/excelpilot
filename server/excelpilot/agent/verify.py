import re
from typing import Any

from excelpilot.agent.jev.gates import judge_claim_support


def split_into_sentences(text: str) -> list[str]:
    # Simple regex sentence splitter
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw if s.strip()]


def has_numerical_claim(sentence: str) -> bool:
    # Check if sentence contains numbers, percentages, or currency
    return bool(re.search(r"(\$|€|£)?\b\d+([.,]\d+)?%?\b", sentence))


async def verify_claims(
    answer_text: str, facts_table: dict[str, Any]
) -> tuple[str, list[dict[str, Any]]]:
    sentences = split_into_sentences(answer_text)
    verification_results: list[dict[str, Any]] = []
    final_sentences: list[str] = []

    for sentence in sentences:
        if not has_numerical_claim(sentence):
            final_sentences.append(sentence)
            continue

        verdict, confidence = await judge_claim_support(sentence, facts_table)
        verification_results.append(
            {
                "sentence": sentence,
                "verdict": verdict,
                "confidence": confidence,
            }
        )

        if verdict == "unsupported":
            # Add warning badge to flagged sentence
            final_sentences.append(f"{sentence} ⚠️")
        else:
            final_sentences.append(sentence)

    return " ".join(final_sentences), verification_results
