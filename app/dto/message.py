from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
