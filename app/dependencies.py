from typing import Annotated
from uuid import UUID

import sqlalchemy as sa
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dao.user_dao import UserDao
from app.logging import logger
from app.models.user import User
from app.security import SecurityService

bearer = HTTPBearer()


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = SecurityService.decode_access_token(credentials.credentials)
        user_id = UUID(payload['sub'])
    except (ValueError, KeyError, TypeError):
        logger.warning('auth_dependency_rejected reason=invalid_token')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
    user = await UserDao.get_by_id(db, user_id)
    if user is None:
        logger.warning('auth_dependency_rejected reason=user_not_found user_id=%s', user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    logger.debug('auth_dependency_completed user_id=%s', user.id)
    return user
