from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.onboarding_dao import OnboardingDao
from app.dao.user_profile_dao import UserProfileDao
from app.dto.onboarding import OnboardingResponse
from app.dto.user import UserProfileResponse
from app.logging import logger
from app.models.onboarding_state import OnboardingState
from app.models.user_profile import UserProfile


class OnboardingService:
    _steps = (
        'companion_gender',
        'user_gender',
        'preferred_address',
        'language',
        'timezone',
    )
    _questions = {
        'companion_gender': 'Кого ты хочешь видеть рядом? Ответь female, если нужен AI-girlfriend, или male в остальных случаях.',
        'user_gender': 'Какой пол учитывать в обращении к тебе? Можно ответить unspecified.',
        'preferred_address': 'Как к тебе обращаться? Напиши имя или обращение, либо «пропустить».',
        'language': 'На каком языке общаться? Ответь ru или en.',
        'timezone': 'В каком часовом поясе ты находишься? Например, Europe/Moscow.',
    }
    _genders = {'male', 'female', 'non_binary', 'unspecified'}

    @classmethod
    async def start(cls: type['OnboardingService'], db: AsyncSession, user_id: UUID) -> OnboardingResponse:
        profile = await UserProfileDao.ensure(db, user_id)
        state = await OnboardingDao.ensure(db, user_id)
        if state.step == 'companion_role':
            state.step = 'companion_gender'
        await db.commit()
        logger.info('onboarding_started user_id=%s step=%s', user_id, state.step)
        return cls._response(profile, state)

    @classmethod
    async def answer(cls: type['OnboardingService'], db: AsyncSession, user_id: UUID, answer: str) -> OnboardingResponse:
        profile = await UserProfileDao.ensure(db, user_id)
        state = await OnboardingDao.ensure(db, user_id)
        if state.step == 'companion_role':
            state.step = 'companion_gender'
        if state.status == 'completed':
            return cls._response(profile, state)
        value = cls._normalize(state.step, answer)
        fields = cls._profile_fields(state.step, value)
        await UserProfileDao.update_preferences(
            db,
            profile,
            fields[0],
            fields[1],
            fields[2],
            fields[3],
            fields[4],
            fields[5],
            fields[6],
        )
        answers = dict(state.answers)
        answers[state.step] = value
        current_index = cls._steps.index(state.step)
        next_step = cls._steps[current_index + 1] if current_index + 1 < len(cls._steps) else 'completed'
        status = 'completed' if next_step == 'completed' else 'in_progress'
        completed_at = datetime.now(timezone.utc).replace(tzinfo=None) if status == 'completed' else None
        await OnboardingDao.advance(db, state, status, next_step, answers, completed_at)
        await db.commit()
        await db.refresh(profile)
        await db.refresh(state)
        logger.info('onboarding_answer_saved user_id=%s step=%s next_step=%s', user_id, state.step, next_step)
        return cls._response(profile, state)

    @classmethod
    async def update_profile(
        cls: type['OnboardingService'],
        db: AsyncSession,
        user_id: UUID,
        companion_role: Optional[str],
        companion_gender: Optional[str],
        user_gender: Optional[str],
        user_pronouns: Optional[str],
        preferred_address: Optional[str],
        language: Optional[str],
        timezone: Optional[str],
    ) -> UserProfileResponse:
        if timezone is not None:
            try:
                ZoneInfo(timezone)
            except ZoneInfoNotFoundError as error:
                raise ValueError('Неизвестный часовой пояс') from error
        profile = await UserProfileDao.ensure(db, user_id)
        await UserProfileDao.update_preferences(
            db,
            profile,
            companion_role,
            companion_gender,
            user_gender,
            user_pronouns,
            preferred_address,
            language,
            timezone,
        )
        await db.commit()
        await db.refresh(profile)
        logger.info('user_profile_updated user_id=%s', user_id)
        return UserProfileResponse.model_validate(profile)

    @classmethod
    def _normalize(cls: type['OnboardingService'], step: str, answer: str) -> str:
        value = answer.strip()
        lowered = value.casefold()
        if not value:
            raise ValueError('Ответ не может быть пустым')
        if step == 'companion_role':
            return 'male'
        if step == 'companion_gender':
            if lowered in {'female', 'girlfriend', 'девушка', 'женщина', 'ж'}:
                return 'female'
            return 'male'
        if step == 'user_gender':
            normalized = lowered.replace('-', '_').replace(' ', '_')
            if normalized not in cls._genders:
                raise ValueError('Используй male, female, non_binary или unspecified')
            return normalized
        if step == 'preferred_address' and lowered in {'пропустить', 'skip', '-', 'нет'}:
            return ''
        if step == 'language':
            if lowered not in {'ru', 'en'}:
                raise ValueError('Поддерживаются языки ru и en')
            return lowered
        if step == 'timezone':
            try:
                ZoneInfo(value)
            except ZoneInfoNotFoundError as error:
                raise ValueError('Неизвестный часовой пояс. Например, Europe/Moscow') from error
            return value
        return value

    @classmethod
    def _profile_fields(cls: type['OnboardingService'], step: str, value: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
        fields: Dict[str, Optional[str]] = {
            'companion_role': None,
            'companion_gender': None,
            'user_gender': None,
            'user_pronouns': None,
            'preferred_address': None,
            'language': None,
            'timezone': None,
        }
        if step == 'companion_gender':
            fields['companion_role'] = 'girlfriend' if value == 'female' else 'boyfriend'
            fields['companion_gender'] = 'female' if value == 'female' else 'male'
        else:
            fields[step] = value
        return (
            fields['companion_role'],
            fields['companion_gender'],
            fields['user_gender'],
            fields['user_pronouns'],
            fields['preferred_address'],
            fields['language'],
            fields['timezone'],
        )

    @classmethod
    def _response(cls: type['OnboardingService'], profile: UserProfile, state: OnboardingState) -> OnboardingResponse:
        return OnboardingResponse(
            status=state.status,
            step=state.step,
            question=cls._questions.get(state.step),
            profile=UserProfileResponse.model_validate(profile),
        )
