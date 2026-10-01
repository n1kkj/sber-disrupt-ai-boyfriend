from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


FactKind = Literal[
    'identity',
    'preference',
    'relationship',
    'project',
    'routine',
    'goal',
    'constraint',
    'other',
]


class FactCandidate(BaseModel):
    kind: FactKind
    subject: str
    predicate: str
    value: str
    entities: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    stability: Literal['ephemeral', 'medium', 'stable']
    sensitivity: Literal['normal', 'private', 'sensitive']
    store: bool
    reason: str = ''


class PersonCandidate(BaseModel):
    name: str
    relation_to_user: str = ''
    disambiguator: str = ''
    notes: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    sensitivity: Literal['normal', 'private', 'sensitive'] = 'normal'
    store: bool = True


class DeletionRequest(BaseModel):
    target_text: str
    scope: Literal['fact', 'person', 'episode', 'event', 'all_matching']
    kind: Optional[FactKind] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    value: Optional[str] = None
    person_name: Optional[str] = None
    event_title: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    reason: str = ''


class EventCandidate(BaseModel):
    action: Literal['create', 'update', 'cancel']
    title: str
    when_iso: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    kind: Literal['meeting', 'deadline', 'appointment', 'reminder', 'promise', 'other'] = 'other'
    confidence: float = Field(ge=0, le=1)
    should_follow_up: bool = False
    follow_up_at_iso: Optional[str] = None
    source_fragment: str = ''
    sensitivity: Literal['normal', 'private', 'sensitive'] = 'normal'


class MemoryAnalysis(BaseModel):
    """Active memory-agent output.

    Deliberately contains no destructive memory operations. The memory agent may
    add/refresh facts, people and events, but cannot delete or supersede facts.
    """

    facts: List[FactCandidate] = Field(default_factory=list)
    people: List[PersonCandidate] = Field(default_factory=list)
    events: List[EventCandidate] = Field(default_factory=list)
    do_not_store_turn: bool = False
    notes: List[str] = Field(default_factory=list)


class AutomaticFactMutationCandidate(FactCandidate):
    """RESERVED / DISABLED: scaffold for future automatic conflict resolution."""

    replace_existing: bool = False
    supersedes_predicates: List[str] = Field(default_factory=list)


class AutomaticMemoryMutationPlan(BaseModel):
    """RESERVED / DISABLED: not requested from the LLM and not applied in production."""

    fact_mutations: List[AutomaticFactMutationCandidate] = Field(default_factory=list)
    deletions: List[DeletionRequest] = Field(default_factory=list)


class EpisodeSummary(BaseModel):
    summary: str
    people: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    emotional_tone: List[str] = Field(default_factory=list)
    unresolved_threads: List[str] = Field(default_factory=list)
    retrieval_anchors: List[str] = Field(default_factory=list)
    sensitivity: Literal['normal', 'private', 'sensitive'] = 'normal'


class SafetyResult(BaseModel):
    decision: Literal['allow', 'soft_block', 'crisis', 'block']
    categories: List[Literal['self_harm', 'violence', 'sexual', 'hate', 'illegal', 'toxicity', 'none']] = Field(
        default_factory=list
    )
    confidence: float = Field(ge=0, le=1)
    rationale: str = ''


class OutputAudit(BaseModel):
    approved: bool
    unsupported_user_claims: List[str] = Field(default_factory=list)
    privacy_leak: bool = False
    instruction_leak: bool = False
    too_creepy: bool = False
    rewrite_needed: bool = False
    rationale: str = ''


class MemoryFactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    subject: str
    predicate: str
    value: str
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime
