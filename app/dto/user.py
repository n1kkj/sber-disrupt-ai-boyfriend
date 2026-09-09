from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    display_name: str | None
    telegram_id: int | None


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    companion_role: str
    companion_gender: str
    user_gender: str
    user_pronouns: str | None
    preferred_address: str | None
    language: str
    timezone: str
    proactive_enabled: bool
    daily_proactive_limit: int


class UserProfileUpdateRequest(BaseModel):
    companion_role: str | None = Field(default=None, pattern='^(boyfriend|girlfriend)$')
    companion_gender: str | None = Field(default=None, pattern='^(male|female|non_binary|unspecified)$')
    user_gender: str | None = Field(default=None, pattern='^(male|female|non_binary|unspecified)$')
    user_pronouns: str | None = Field(default=None, max_length=120)
    preferred_address: str | None = Field(default=None, max_length=120)
    language: str | None = Field(default=None, pattern='^(ru|en)$')
    timezone: str | None = Field(default=None, max_length=64)
