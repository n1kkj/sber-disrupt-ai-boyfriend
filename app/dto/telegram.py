from datetime import datetime

from pydantic import BaseModel, Field


class TelegramLinkResponse(BaseModel):
    url: str
    expires_at: datetime


class TelegramClaimRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
