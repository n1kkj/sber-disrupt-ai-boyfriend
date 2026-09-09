from app.dto.auth import AuthResponse, LoginRequest, RegisterRequest
from app.dto.boyfriend import BoyfriendResponse
from app.dto.chat import ChatCreateRequest, ChatResponse
from app.dto.message import MessageRequest, MessageResponse, MessageTaskResponse
from app.dto.telegram import TelegramClaimRequest, TelegramLinkResponse
from app.dto.user import UserProfileResponse, UserProfileUpdateRequest, UserResponse
from app.dto.onboarding import OnboardingAnswerRequest, OnboardingResponse

__all__ = ['AuthResponse', 'LoginRequest', 'RegisterRequest', 'BoyfriendResponse', 'ChatCreateRequest', 'ChatResponse', 'MessageRequest', 'MessageResponse', 'MessageTaskResponse', 'TelegramClaimRequest', 'TelegramLinkResponse', 'UserResponse', 'UserProfileResponse', 'UserProfileUpdateRequest', 'OnboardingAnswerRequest', 'OnboardingResponse']
