from uuid import UUID

from pydantic import BaseModel

from app.dto.message import MessageResponse


class MediaTaskResponse(BaseModel):
    message: MessageResponse
    asset_id: UUID
    task_id: str
    processing_status: str
