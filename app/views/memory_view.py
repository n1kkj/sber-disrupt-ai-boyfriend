from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import current_user
from app.dto.memory import MemoryFactResponse
from app.models.memory_item import MemoryItem
from app.models.user import User
from app.services.memory_fact_service import MemoryFactService

router = APIRouter(prefix='/memory', tags=['memory'])


@router.get('/facts', response_model=List[MemoryFactResponse])
async def list_memory_facts(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MemoryItem]:
    return await MemoryFactService.list_user_facts(db, user.id)


@router.delete('/facts/{fact_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory_fact(
    fact_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await MemoryFactService.delete_user_fact(db, user.id, fact_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
