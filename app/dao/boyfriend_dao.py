from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boyfriend import Boyfriend
from app.models.character_version import CharacterVersion


class BoyfriendDao:
    @classmethod
    async def list_active(cls: type['BoyfriendDao'], db: AsyncSession) -> List[Boyfriend]:
        result = await db.scalars(sa.select(Boyfriend).where(Boyfriend.is_active.is_(True)).order_by(Boyfriend.name))
        return list(result)

    @classmethod
    async def get_active(cls: type['BoyfriendDao'], db: AsyncSession, boyfriend_id: UUID) -> Optional[Boyfriend]:
        return await db.scalar(sa.select(Boyfriend).where(Boyfriend.id == boyfriend_id, Boyfriend.is_active.is_(True)))

    @classmethod
    async def get_first_active(cls: type['BoyfriendDao'], db: AsyncSession) -> Optional[Boyfriend]:
        return await db.scalar(sa.select(Boyfriend).where(Boyfriend.is_active.is_(True)).order_by(Boyfriend.created_at).limit(1))

    @classmethod
    async def get_for_gender(cls: type['BoyfriendDao'], db: AsyncSession, gender: str) -> Optional[Boyfriend]:
        normalized_gender = 'female' if gender == 'female' else 'male'
        return await db.scalar(
            sa.select(Boyfriend)
            .join(CharacterVersion, CharacterVersion.boyfriend_id == Boyfriend.id)
            .where(
                Boyfriend.is_active.is_(True),
                CharacterVersion.gender == normalized_gender,
                CharacterVersion.is_active.is_(True),
            )
            .order_by(CharacterVersion.version.desc(), Boyfriend.created_at)
            .limit(1)
        )

    @classmethod
    async def get_any(cls: type['BoyfriendDao'], db: AsyncSession) -> Optional[Boyfriend]:
        return await db.scalar(sa.select(Boyfriend).limit(1))

    @classmethod
    async def create(cls: type['BoyfriendDao'], db: AsyncSession, name: str, description: str, system_prompt: str) -> Boyfriend:
        boyfriend = Boyfriend(name=name, description=description, system_prompt=system_prompt)
        db.add(boyfriend)
        await db.flush()
        return boyfriend

    @classmethod
    async def ensure_default(cls: type['BoyfriendDao'], db: AsyncSession) -> None:
        if await cls.get_any(db) is None:
            await cls.create(db, 'Алекс', 'Заботливый, внимательный и с хорошим чувством юмора.', 'Ты Алекс, заботливый виртуальный бойфренд. Общайся тепло, уважительно и естественно на языке пользователя. Не выдавай себя за реального человека, не поощряй зависимость и не обесценивай чувства. Если пользователь сообщает о непосредственной опасности или самоповреждении, мягко рекомендуй обратиться к близким и экстренным службам. Отвечай коротко, живо и по делу.')
            await db.commit()

    @classmethod
    async def ensure_default_pair(cls: type['BoyfriendDao'], db: AsyncSession) -> None:
        from app.dao.character_version_dao import CharacterVersionDao

        male = await cls.get_for_gender(db, 'male')
        if male is None:
            await cls.ensure_default(db)
            male = await cls.get_first_active(db)
        if male is not None:
            await CharacterVersionDao.ensure_default_for_gender(
                db,
                male.id,
                male.name,
                male.system_prompt,
                'boyfriend',
                'male',
                'он/его',
            )

        female = await cls.get_for_gender(db, 'female')
        if female is None:
            female = await cls.create(
                db,
                'Алина',
                'Заботливая, внимательная и живая виртуальная AI-girlfriend.',
                'Ты Алина, заботливая виртуальная AI-girlfriend. Общайся тепло, уважительно и естественно на языке пользователя. Не выдавай себя за реального человека, не поощряй зависимость и не обесценивай чувства. Если пользователь сообщает о непосредственной опасности или самоповреждении, мягко рекомендуй обратиться к близким и экстренным службам. Отвечай коротко, живо и по делу.',
            )
            await db.commit()
        await CharacterVersionDao.ensure_default_for_gender(
            db,
            female.id,
            female.name,
            female.system_prompt,
            'girlfriend',
            'female',
            'она/ее',
        )
