from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .config import settings
from .discovery import search_discovery
from .llm import get_chat_model
from .retrieval import search_whitelist
from .schemas import (
    DraftResponse,
    InputItem,
    InvestigationResult,
    NormalizationResult,
    PipelineState,
    TriageDecision,
)
from .storage import save_run
from .utils import clean_text, keyword_health_score, normalize_language_code, short_snippet


NORMALIZER_PROMPT = """
You are a public health intake normalizer for Tunisia.
The input may be in English, French, Arabic, Tunisian dialect, or Arabizi.
Return JSON only.
Tasks:
1. Detect language as fr, en, ar, mixed, or unknown.
2. Rewrite the main health claim or event as one short neutral sentence.
3. Score health relevance from 0 to 1.
""".strip()


TRIAGE_PROMPT = """
You are a triage analyst in a health infodemic monitoring cell.
Classify the item into exactly one category:
- real_alert: outbreak report, symptoms cluster, official warning, or genuine health incident needing escalation.
- rumor_infodemie: false or misleading health claim, pseudo-treatment, anti-vaccine rumor, or content that may trigger risky behavior.
- weak_signal: health-related but ambiguous, incomplete, or not yet actionable.
- irrelevant: not health related.
Return JSON only.
""".strip()


INVESTIGATION_PROMPT = """
You are an evidence-grounded public health investigator.
You will receive two evidence groups:
1. OFFICIAL WHITELIST EVIDENCE: trusted health sources used to judge factual support or contradiction.
2. RECENT CONTEXT EVIDENCE: crawled web/social items used only to understand current phrasing, spread, and signal context.
Rules:
- Use official whitelist evidence as the source of factual truth.
- Use recent context evidence only as supplementary situational awareness.
- Never treat recent context evidence alone as proof that a health claim is true.
- If official whitelist evidence is insufficient, verdict must be uncertain.
Return JSON only.
""".strip()


def _append_trace(state: PipelineState, message: str) -> list[str]:
    trace = list(state.get("trace", []))
    trace.append(message)
    return trace


def _state_item(state: PipelineState) -> InputItem:
    raw_item = state.get("item", {})
    return InputItem(**raw_item)


def normalize_node(state: PipelineState) -> dict[str, Any]:
    item = _state_item(state)
    content = clean_text(f"Title: {item.title}\nSource: {item.source}\nText: {item.text}")
    llm = get_chat_model(temperature=0)
    structured = llm.with_structured_output(NormalizationResult)
    keyword_score = keyword_health_score(content)
    try:
        result = structured.invoke(
            [
                ("system", NORMALIZER_PROMPT),
                ("human", content[:5000]),
            ]
        )
        language = normalize_language_code(result.language)
        normalized_claim = clean_text(result.normalized_claim) or short_snippet(item.text, 200)
        health_relevance = max(keyword_score, float(result.health_relevance))
    except Exception:
        language = "unknown"
        normalized_claim = short_snippet(item.text or item.title, 200)
        health_relevance = keyword_score

    return {
        "language": language,
        "normalized_claim": normalized_claim,
        "health_relevant": health_relevance >= 0.25,
        "trace": _append_trace(
            state,
            f"normalize: language={language} health_relevance={round(health_relevance, 3)}",
        ),
    }


def route_after_normalize(state: PipelineState) -> str:
    return "triage" if state.get("health_relevant", False) else "finalize"


def triage_node(state: PipelineState) -> dict[str, Any]:
    item = _state_item(state)
    llm = get_chat_model(temperature=0)
    structured = llm.with_structured_output(TriageDecision)

    prompt = (
        f"Normalized claim: {state.get('normalized_claim', '')}\n"
        f"Source: {item.source}\n"
        f"Title: {item.title}\n"
        f"Text: {item.text[:4000]}"
    )

    heuristic_text = f"{item.title} {item.text}".lower()
    try:
        result = structured.invoke(
            [
                ("system", TRIAGE_PROMPT),
                ("human", prompt),
            ]
        )
        triage = result.model_dump()
    except Exception:
        category = "weak_signal"
        risk = "medium"
        if any(token in heuristic_text for token in ["autism", "miracle cure", "fake", "hoax", "anti vaccine"]):
            category = "rumor_infodemie"
            risk = "high"
        elif any(token in heuristic_text for token in ["cluster", "symptoms", "outbreak", "fever", "rash"]):
            category = "real_alert"
            risk = "high"
        triage = TriageDecision(
            category=category,
            risk_level=risk,
            primary_claim=state.get("normalized_claim", item.title or item.text[:160]),
            reasoning="Fallback heuristic classification used.",
            keywords=[word for word in ["measles", "vaccine", "fever", "rash"] if word in heuristic_text],
            requires_public_response=category == "rumor_infodemie",
            requires_human_review=True,
        ).model_dump()

    return {
        "triage": triage,
        "trace": _append_trace(state, f"triage: category={triage['category']} risk={triage['risk_level']}"),
    }


def _build_query_from_state(state: PipelineState) -> str:
    triage = state.get("triage", {})
    investigation = state.get("investigation", {})
    base_query = clean_text(
        investigation.get("follow_up_query", "")
        or triage.get("primary_claim", "")
        or state.get("normalized_claim", "")
    )
    keywords = " ".join(triage.get("keywords", [])[:5])
    return clean_text(f"{base_query} {keywords}")


def retrieve_evidence_node(state: PipelineState) -> dict[str, Any]:
    query = _build_query_from_state(state)
    evidence = search_whitelist(query=query, top_k=settings.top_k_evidence)
    return {
        "evidence": [chunk.model_dump() for chunk in evidence],
        "trace": _append_trace(state, f"retrieve_whitelist: query={query!r} top_k={len(evidence)}"),
    }


def retrieve_context_node(state: PipelineState) -> dict[str, Any]:
    query = _build_query_from_state(state)
    context_evidence = search_discovery(query=query, top_k=settings.top_k_context)
    return {
        "context_evidence": [chunk.model_dump() for chunk in context_evidence],
        "trace": _append_trace(state, f"retrieve_context: query={query!r} top_k={len(context_evidence)}"),
    }


def investigate_node(state: PipelineState) -> dict[str, Any]:
    triage = state.get("triage", {})
    official_evidence = state.get("evidence", [])
    context_evidence = state.get("context_evidence", [])
    llm = get_chat_model(temperature=0)
    structured = llm.with_structured_output(InvestigationResult)

    official_block = "\n\n".join(
        [
            f"[OFFICIAL {row['chunk_id']}] {row['source_title']} | {row.get('source_url', '')}\n{row['text'][:1200]}"
            for row in official_evidence
        ]
    )
    context_block = "\n\n".join(
        [
            f"[CONTEXT {row['chunk_id']}] {row['source_title']} | {row.get('source_type', '')} | {row.get('source_url', '')}\n{row['text'][:800]}"
            for row in context_evidence
        ]
    )
    prompt = (
        f"Primary claim: {triage.get('primary_claim', state.get('normalized_claim', ''))}\n"
        f"Category from triage: {triage.get('category', '')}\n\n"
        f"OFFICIAL WHITELIST EVIDENCE:\n{official_block or '[none]'}\n\n"
        f"RECENT CONTEXT EVIDENCE:\n{context_block or '[none]'}"
    )

    try:
        result = structured.invoke(
            [
                ("system", INVESTIGATION_PROMPT),
                ("human", prompt[:14000]),
            ]
        )
        investigation = result.model_dump()
    except Exception:
        top_chunk_id = official_evidence[0]["chunk_id"] if official_evidence else ""
        investigation = InvestigationResult(
            verdict="uncertain",
            confidence=0.4,
            analysis="Fallback path: model failed to return structured investigation.",
            public_health_risk="Needs human review before action.",
            evidence_used=[top_chunk_id] if top_chunk_id else [],
            follow_up_query=triage.get("primary_claim", state.get("normalized_claim", "")),
        ).model_dump()

    return {
        "investigation": investigation,
        "trace": _append_trace(
            state,
            "investigate: "
            f"official={len(official_evidence)} context={len(context_evidence)} "
            f"verdict={investigation['verdict']} confidence={investigation['confidence']}",
        ),
    }


def quality_gate_node(state: PipelineState) -> dict[str, Any]:
    attempts = int(state.get("attempts", 0))
    official_evidence = state.get("evidence", [])
    context_evidence = state.get("context_evidence", [])
    triage = state.get("triage", {})
    investigation = state.get("investigation", {})

    need_more_evidence = False
    if investigation.get("verdict") == "uncertain" and attempts < 1:
        need_more_evidence = True
    if len(official_evidence) < 2 and attempts < 1:
        need_more_evidence = True
    if len(official_evidence) == 0 and len(context_evidence) > 0 and attempts < 1:
        need_more_evidence = True

    needs_human_review = bool(triage.get("requires_human_review", True))
    if investigation.get("verdict") == "uncertain":
        needs_human_review = True

    return {
        "attempts": attempts + 1 if need_more_evidence else attempts,
        "need_more_evidence": need_more_evidence,
        "needs_human_review": needs_human_review,
        "trace": _append_trace(
            state,
            "quality_gate: "
            f"official={len(official_evidence)} context={len(context_evidence)} "
            f"need_more_evidence={need_more_evidence} needs_human_review={needs_human_review}",
        ),
    }


def route_after_quality(state: PipelineState) -> str:
    triage = state.get("triage", {})
    investigation = state.get("investigation", {})
    category = triage.get("category")
    verdict = investigation.get("verdict")

    if category == "irrelevant":
        return "finalize"
    if state.get("need_more_evidence"):
        return "retrieve_evidence"
    if category == "rumor_infodemie" or verdict == "contradicted":
        return "draft_counter"
    if category == "real_alert" and verdict in {"supported", "uncertain"}:
        return "draft_alert"
    return "finalize"


def draft_counter_node(state: PipelineState) -> dict[str, Any]:
    triage = state.get("triage", {})
    investigation = state.get("investigation", {})
    evidence = state.get("evidence", [])
    output_language = state.get("output_language", settings.output_language)

    evidence_lines = "\n".join(
        f"- {row['source_title']} ({row.get('source_url', '')}) [{row['chunk_id']}]"
        for row in evidence[:4]
    )
    llm = get_chat_model(temperature=0.1)
    structured = llm.with_structured_output(DraftResponse)
    prompt = f"""
Write a concise public-health counter message in language code: {output_language}.
Claim: {triage.get('primary_claim', '')}
Investigation verdict: {investigation.get('verdict', '')}
Analysis: {investigation.get('analysis', '')}
Risk: {investigation.get('public_health_risk', '')}
Available official evidence sources:
{evidence_lines}
Requirements:
- Be calm and professional.
- Use 4 short parts: warning, why misleading, what the evidence says, what people should do.
- Do not invent facts beyond the investigation and evidence list.
Return JSON only.
""".strip()
    try:
        result = structured.invoke([("system", "You write safe public health responses."), ("human", prompt)])
        draft = result.model_dump()
    except Exception:
        draft = DraftResponse(
            headline="Counter message draft",
            public_message=(
                f"Warning: this claim should not be trusted without verification. "
                f"Our current review found the claim '{triage.get('primary_claim', '')}' to be {investigation.get('verdict', 'uncertain')}. "
                "Please refer to official health sources and consult a qualified health professional."
            ),
            internal_brief="Fallback counter-message generated because structured output failed.",
        ).model_dump()
    return {
        "draft": draft,
        "final_status": "counter_message_ready",
        "trace": _append_trace(state, "draft_counter: completed"),
    }


def draft_alert_node(state: PipelineState) -> dict[str, Any]:
    triage = state.get("triage", {})
    investigation = state.get("investigation", {})
    evidence = state.get("evidence", [])
    context_evidence = state.get("context_evidence", [])
    evidence_lines = "\n".join(
        f"- {row['source_title']} ({row.get('source_url', '')}) [{row['chunk_id']}]"
        for row in evidence[:4]
    )
    context_lines = "\n".join(
        f"- {row['source_title']} ({row.get('source_type', '')}) [{row['chunk_id']}]"
        for row in context_evidence[:4]
    )
    brief = (
        f"Analyst brief\n"
        f"Category: {triage.get('category', '')}\n"
        f"Risk: {triage.get('risk_level', '')}\n"
        f"Claim/Event: {triage.get('primary_claim', '')}\n"
        f"Verdict: {investigation.get('verdict', '')}\n"
        f"Analysis: {investigation.get('analysis', '')}\n"
        f"Next step: escalate to human validator and compare with field surveillance.\n"
        f"Official evidence:\n{evidence_lines or '- none'}\n"
        f"Recent context:\n{context_lines or '- none'}"
    )
    return {
        "analyst_brief": brief,
        "final_status": "alert_brief_ready",
        "trace": _append_trace(state, "draft_alert: completed"),
    }


def finalize_node(state: PipelineState) -> dict[str, Any]:
    status = state.get("final_status") or "analysis_complete"
    payload = dict(state)
    payload["final_status"] = status
    run_id = save_run(payload, run_id=state.get("run_id"))
    return {
        "run_id": run_id,
        "final_status": status,
        "trace": _append_trace(state, f"finalize: run_id={run_id}"),
    }


def build_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("normalize", normalize_node)
    graph.add_node("triage", triage_node)
    graph.add_node("retrieve_evidence", retrieve_evidence_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("investigate", investigate_node)
    graph.add_node("quality_gate", quality_gate_node)
    graph.add_node("draft_counter", draft_counter_node)
    graph.add_node("draft_alert", draft_alert_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "normalize")
    graph.add_conditional_edges(
        "normalize",
        route_after_normalize,
        {
            "triage": "triage",
            "finalize": "finalize",
        },
    )
    graph.add_edge("triage", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "retrieve_context")
    graph.add_edge("retrieve_context", "investigate")
    graph.add_edge("investigate", "quality_gate")
    graph.add_conditional_edges(
        "quality_gate",
        route_after_quality,
        {
            "retrieve_evidence": "retrieve_evidence",
            "draft_counter": "draft_counter",
            "draft_alert": "draft_alert",
            "finalize": "finalize",
        },
    )
    graph.add_edge("draft_counter", "finalize")
    graph.add_edge("draft_alert", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


PIPELINE = build_pipeline()


def run_pipeline(item: InputItem | dict[str, Any], output_language: str | None = None) -> dict[str, Any]:
    if isinstance(item, InputItem):
        item_payload = item.model_dump()
    else:
        item_payload = InputItem(**item).model_dump()

    initial_state: PipelineState = {
        "item": item_payload,
        "output_language": output_language or settings.output_language,
        "attempts": 0,
        "trace": [],
    }
    return PIPELINE.invoke(initial_state)
