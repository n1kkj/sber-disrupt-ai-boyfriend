from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatCreateRequest(BaseModel):
    boyfriend_id: UUID
    title: Optional[str] = Field(default=None, max_length=160)


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    boyfriend_id: UUID
    title: Optional[str]
