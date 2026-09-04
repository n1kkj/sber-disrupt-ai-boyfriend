from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boyfriend import Boyfriend


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
