from pydantic import BaseModel, Field

from app.dto.user import UserProfileResponse


class OnboardingAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=500)


class OnboardingResponse(BaseModel):
    status: str
    step: str
    question: str | None
    profile: UserProfileResponse
