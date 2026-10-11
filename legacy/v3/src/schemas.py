from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class InputItem(BaseModel):
    title: str = ""
    text: str
    url: str = ""
    source: str = "manual"
    published: str = ""
    source_type: str = "manual"
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizationResult(BaseModel):
    language: Literal["fr", "en", "ar", "mixed", "unknown"] = "unknown"
    normalized_claim: str = Field(description="Short neutral summary of the main health claim or event.")
    health_relevance: float = Field(ge=0.0, le=1.0, description="How health-related the content is.")


class TriageDecision(BaseModel):
    category: Literal["real_alert", "rumor_infodemie", "weak_signal", "irrelevant"]
    risk_level: Literal["low", "medium", "high", "critical"]
    primary_claim: str
    reasoning: str
    keywords: list[str] = Field(default_factory=list)
    requires_public_response: bool = False
    requires_human_review: bool = True


class EvidenceChunk(BaseModel):
    chunk_id: str
    source_title: str
    source_url: str = ""
    text: str
    score: float
    source_type: str = ""


class InvestigationResult(BaseModel):
    verdict: Literal["supported", "contradicted", "uncertain"]
    confidence: float = Field(ge=0.0, le=1.0)
    analysis: str
    public_health_risk: str
    evidence_used: list[str] = Field(default_factory=list)
    follow_up_query: str = ""


class DraftResponse(BaseModel):
    headline: str
    public_message: str
    internal_brief: str


class PipelineState(TypedDict, total=False):
    item: dict[str, Any]
    output_language: str
    attempts: int
    normalized_claim: str
    language: str
    health_relevant: bool
    triage: dict[str, Any]
    evidence: list[dict[str, Any]]
    context_evidence: list[dict[str, Any]]
    investigation: dict[str, Any]
    draft: dict[str, Any]
    analyst_brief: str
    final_status: str
    need_more_evidence: bool
    needs_human_review: bool
    trace: list[str]
    run_id: str
