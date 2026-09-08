from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.boyfriend_dao import BoyfriendDao
from app.logging import logger
from app.models.boyfriend import Boyfriend


class BoyfriendService:
    @classmethod
    async def list_active(cls: type['BoyfriendService'], db: AsyncSession) -> List[Boyfriend]:
        logger.info('companion_list_started')
        boyfriends = await BoyfriendDao.list_active(db)
        logger.info('companion_list_completed count=%s', len(boyfriends))
        return boyfriends
