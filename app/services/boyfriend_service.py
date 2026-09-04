from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.boyfriend_dao import BoyfriendDao
from app.models.boyfriend import Boyfriend


class BoyfriendService:
    def __init__(self, boyfriend_dao: BoyfriendDao) -> None:
        self.boyfriend_dao = boyfriend_dao

    async def list_active(self, db: AsyncSession) -> List[Boyfriend]:
        return await self.boyfriend_dao.list_active(db)
