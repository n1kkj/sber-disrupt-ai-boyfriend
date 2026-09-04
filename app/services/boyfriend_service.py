from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.boyfriend_dao import BoyfriendDao
from app.models.boyfriend import Boyfriend


class BoyfriendService:
    @classmethod
    async def list_active(cls: type['BoyfriendService'], db: AsyncSession) -> List[Boyfriend]:
        return await BoyfriendDao.list_active(db)
