from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    display_name: str | None
    telegram_id: int | None
