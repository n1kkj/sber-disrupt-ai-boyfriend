from app.dto.auth import AuthResponse, LoginRequest, RegisterRequest
from app.dto.boyfriend import BoyfriendResponse
from app.dto.chat import ChatCreateRequest, ChatResponse
from app.dto.memory import MemoryFactResponse
from app.dto.message import MessageRequest, MessageResponse, MessageTaskResponse
from app.dto.onboarding import OnboardingAnswerRequest, OnboardingResponse
from app.dto.telegram import TelegramClaimRequest, TelegramLinkResponse
from app.dto.user import UserProfileResponse, UserProfileUpdateRequest, UserResponse

__all__ = [
    'AuthResponse',
    'LoginRequest',
    'RegisterRequest',
    'BoyfriendResponse',
    'ChatCreateRequest',
    'ChatResponse',
    'MemoryFactResponse',
    'MessageRequest',
    'MessageResponse',
    'MessageTaskResponse',
    'TelegramClaimRequest',
    'TelegramLinkResponse',
    'UserResponse',
    'UserProfileResponse',
    'UserProfileUpdateRequest',
    'OnboardingAnswerRequest',
    'OnboardingResponse',
]
