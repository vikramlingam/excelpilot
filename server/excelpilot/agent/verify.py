import re
from typing import Any

from excelpilot.agent.jev.gates import judge_claim_support


def split_into_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw if s.strip()]


def has_numerical_claim(sentence: str) -> bool:
    return bool(re.search(r"(\$|€|£)?\b\d+([.,]\d+)?%?\b", sentence))


def compact_facts(facts_table: dict[str, Any], limit: int = 12) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for i, (key, value) in enumerate(facts_table.items()):
        if i >= limit:
            break
        compact[key] = str(value)[:400]
    return compact


async def verify_claims(
    answer_text: str, facts_table: dict[str, Any]
) -> tuple[str, list[dict[str, Any]]]:
    if not facts_table:
        return answer_text, []

    sentences = split_into_sentences(answer_text)
    verification_results: list[dict[str, Any]] = []
    final_sentences: list[str] = []
    facts = compact_facts(facts_table)
    checked = 0

    for sentence in sentences:
        if checked >= 8 or not has_numerical_claim(sentence):
            final_sentences.append(sentence)
            continue
        verdict, confidence = await judge_claim_support(sentence, facts)
        checked += 1
        verification_results.append(
            {"sentence": sentence, "verdict": verdict, "confidence": confidence}
        )
        if verdict == "unsupported":
            final_sentences.append(f"{sentence} ⚠️")
        else:
            final_sentences.append(sentence)

    return " ".join(final_sentences), verification_results
