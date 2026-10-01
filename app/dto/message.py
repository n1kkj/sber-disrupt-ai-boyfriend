from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    scheduled_at: datetime | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role: str
    content: str
    platform: str
    message_type: str
    status: str
    external_id: str | None
    scheduled_at: datetime | None
    created_at: datetime

    @field_serializer('content')
    def serialize_content(self, value: str) -> str:
        return value.replace('[[MESSAGE_BREAK]]', '\n\n').replace('[[SEND_STICKER]]', '').replace('[Стикер]', '')


class MessageTaskResponse(BaseModel):
    message: MessageResponse
    task_id: str | None
    task_status: str
