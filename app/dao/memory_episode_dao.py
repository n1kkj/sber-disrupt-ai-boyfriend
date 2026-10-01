from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.memory import EpisodeSummary
from app.models.memory_episode import MemoryEpisode


class MemoryEpisodeDao:
    @classmethod
    async def list_active(
        cls: type['MemoryEpisodeDao'],
        db: AsyncSession,
        user_id: UUID,
        limit: int = 100,
    ) -> List[MemoryEpisode]:
        result = await db.scalars(
            sa.select(MemoryEpisode)
            .where(MemoryEpisode.user_id == user_id, MemoryEpisode.status == 'active')
            .order_by(MemoryEpisode.created_at.desc())
            .limit(limit)
        )
        return list(result)

    @classmethod
    async def get_by_source_message_id(
        cls: type['MemoryEpisodeDao'],
        db: AsyncSession,
        source_message_id: UUID,
    ) -> Optional[MemoryEpisode]:
        return await db.scalar(
            sa.select(MemoryEpisode).where(MemoryEpisode.source_message_id == source_message_id)
        )

    @classmethod
    async def create(
        cls: type['MemoryEpisodeDao'],
        db: AsyncSession,
        user_id: UUID,
        chat_id: UUID,
        summary: EpisodeSummary,
        source_message_id: UUID,
    ) -> MemoryEpisode:
        episode = MemoryEpisode(
            user_id=user_id,
            chat_id=chat_id,
            summary=summary.summary,
            people=summary.people,
            topics=summary.topics,
            emotional_tone=summary.emotional_tone,
            unresolved_threads=summary.unresolved_threads,
            retrieval_anchors=summary.retrieval_anchors,
            sensitivity=summary.sensitivity,
            status='active',
            source_message_id=source_message_id,
        )
        db.add(episode)
        await db.flush()
        return episode

    @classmethod
    async def mark_deleted(
        cls: type['MemoryEpisodeDao'],
        db: AsyncSession,
        episode: MemoryEpisode,
    ) -> MemoryEpisode:
        episode.status = 'deleted'
        await db.flush()
        return episode
