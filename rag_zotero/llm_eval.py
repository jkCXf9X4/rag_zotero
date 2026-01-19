from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvalItem:
    idx: int
    score: float
    rationale: str


@dataclass(frozen=True)
class EvalReport:
    provider: str
    model: str
    items: list[EvalItem]


def _extract_json_object(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def evaluate_relevance_openrouter(
    *,
    api_key: str,
    model: str,
    query: str,
    candidates: list[dict[str, Any]],
    insecure: bool = False,
    timeout_s: float = 30.0,
) -> EvalReport:
    from openai import OpenAI

    http_client = None
    if insecure:
        import httpx

        http_client = httpx.Client(verify=False, timeout=timeout_s)

    headers = {"X-Title": os.getenv("OPENROUTER_APP_NAME", "rag-zotero")}
    if referer := (os.getenv("OPENROUTER_HTTP_REFERER") or "").strip():
        headers["HTTP-Referer"] = referer

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=headers,
        timeout=timeout_s,
        http_client=http_client,
    )

    system = (
        "You are a strict evaluator for retrieval results.\n"
        "Given a user query and a list of retrieved snippets, score how well each snippet helps "
        "answer the query.\n"
        "Return ONLY valid JSON (no markdown) with schema:\n"
        '{ "items": [ { "idx": <int>, "score": <float 0..1>, "rationale": <string> } ] }\n'
        "The score result should map against the following scale: ~1.0 for directly answering, ~0.5 for tangentially useful, ~0.0 for irrelevant."
    )
    user = {
        "query": query,
        "candidates": candidates,
    }

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        # extra_body={"reasoning": {"enabled": True}},
        temperature=0,
        max_tokens=800,
    )

    content = (resp.choices[0].message.content or "").strip()
    data = _extract_json_object(content)
    if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
        raise ValueError("OpenRouter evaluator returned unexpected JSON shape")

    items: list[EvalItem] = []
    for raw in data["items"]:
        if not isinstance(raw, dict):
            continue
        idx = int(raw.get("idx"))
        score = float(raw.get("score"))
        rationale = str(raw.get("rationale") or "").strip()
        items.append(EvalItem(idx=idx, score=score, rationale=rationale))

    return EvalReport(provider="openrouter", model=model, items=items)
