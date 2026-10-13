"""Stable review contracts, separate from flexible development record storage."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict
Status=Literal['supported','contradicted','misleading','insufficient_evidence','conflicting_evidence','not_factual','unassessed']
class EvidenceLink(BaseModel):
    model_config=ConfigDict(extra='forbid')
    document_id:str
    document_version:int=Field(ge=1)
    passage_id:str
    relation:Literal['supports','contradicts','context']
    relevance_reason:str=Field(min_length=5,max_length=5000)
class AssessmentProposal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    proposed_status:Status
    rationale:str=Field(min_length=10,max_length=10000)
    evidence_links:list[EvidenceLink]=Field(max_length=20)
    limitations:list[str]=Field(min_length=1,max_length=20)
class LanguageSpan(BaseModel):
    start:int=Field(ge=0)
    end:int=Field(ge=1)
    language:Literal['fr','en','ar','derja','derja-latin','mixed','unknown']
