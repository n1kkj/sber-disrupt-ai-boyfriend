from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import current_user
from app.dto.onboarding import OnboardingAnswerRequest, OnboardingResponse
from app.dto.user import UserProfileResponse, UserProfileUpdateRequest
from app.logging import logger
from app.models.user import User
from app.services.onboarding_service import OnboardingService


router = APIRouter(prefix='/onboarding', tags=['onboarding'])


@router.get('', response_model=OnboardingResponse)
async def get_onboarding(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> OnboardingResponse:
    logger.info('onboarding_get_started user_id=%s', user.id)
    return await OnboardingService.start(db, user.id)


@router.post('/answer', response_model=OnboardingResponse)
async def answer_onboarding(
    payload: OnboardingAnswerRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingResponse:
    logger.info('onboarding_answer_started user_id=%s', user.id)
    try:
        response = await OnboardingService.answer(db, user.id, payload.answer)
    except ValueError as error:
        logger.warning('onboarding_answer_rejected user_id=%s reason=%s', user.id, error)
        raise HTTPException(status_code=400, detail=str(error))
    logger.info('onboarding_answer_completed user_id=%s step=%s', user.id, response.step)
    return response


@router.patch('/profile', response_model=UserProfileResponse)
async def update_profile(
    payload: UserProfileUpdateRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    logger.info('profile_update_started user_id=%s', user.id)
    try:
        return await OnboardingService.update_profile(
            db,
            user.id,
            payload.companion_role,
            payload.companion_gender,
            payload.user_gender,
            payload.user_pronouns,
            payload.preferred_address,
            payload.language,
            payload.timezone,
        )
    except ValueError as error:
        logger.warning('profile_update_rejected user_id=%s reason=%s', user.id, error)
        raise HTTPException(status_code=400, detail=str(error))
