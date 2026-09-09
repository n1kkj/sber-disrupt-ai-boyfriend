from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character_version import CharacterVersion


class CharacterVersionDao:
    @classmethod
    async def get_active(cls: type['CharacterVersionDao'], db: AsyncSession, boyfriend_id: UUID) -> Optional[CharacterVersion]:
        return await db.scalar(
            sa.select(CharacterVersion)
            .where(CharacterVersion.boyfriend_id == boyfriend_id, CharacterVersion.is_active.is_(True))
            .order_by(CharacterVersion.version.desc())
            .limit(1)
        )

    @classmethod
    async def create(
        cls: type['CharacterVersionDao'],
        db: AsyncSession,
        boyfriend_id: UUID,
        version: int,
        display_name: str,
        style: str,
        boundaries: str,
        system_prompt: str,
        role_type: str,
        gender: str,
        pronouns: Optional[str],
        voice_profile: Optional[str],
        prompt_version: str,
    ) -> CharacterVersion:
        character = CharacterVersion(
            boyfriend_id=boyfriend_id,
            version=version,
            display_name=display_name,
            style=style,
            boundaries=boundaries,
            system_prompt=system_prompt,
            role_type=role_type,
            gender=gender,
            pronouns=pronouns,
            voice_profile=voice_profile,
            prompt_version=prompt_version,
        )
        db.add(character)
        await db.flush()
        return character

    @classmethod
    async def ensure_default(cls: type['CharacterVersionDao'], db: AsyncSession, boyfriend_id: UUID, name: str, system_prompt: str) -> CharacterVersion:
        active = await cls.get_active(db, boyfriend_id)
        if active is not None:
            return active
        character = await cls.create(
            db,
            boyfriend_id,
            1,
            name,
            'Тёплый, внимательный, живой и уважительный стиль общения.',
            'Не выдавай себя за реального человека, не поощряй зависимость и не нарушай границы пользователя.',
            system_prompt,
            'boyfriend',
            'male',
            'он/его',
            None,
            'v1',
        )
        await db.commit()
        await db.refresh(character)
        return character
