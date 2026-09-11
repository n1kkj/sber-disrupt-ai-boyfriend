from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_asset import MediaAsset


class MediaAssetDao:
    @classmethod
    async def create(
        cls: type['MediaAssetDao'],
        db: AsyncSession,
        message_id: UUID,
        platform: str,
        external_file_id: Optional[str] = None,
        storage_key: Optional[str] = None,
        mime_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
        duration_seconds: Optional[int] = None,
    ) -> MediaAsset:
        asset = MediaAsset(
            message_id=message_id,
            platform=platform,
            external_file_id=external_file_id,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            duration_seconds=duration_seconds,
        )
        db.add(asset)
        await db.flush()
        return asset

    @classmethod
    async def list_for_message(cls: type['MediaAssetDao'], db: AsyncSession, message_id: UUID) -> List[MediaAsset]:
        result = await db.scalars(sa.select(MediaAsset).where(MediaAsset.message_id == message_id).order_by(MediaAsset.created_at))
        return list(result)

    @classmethod
    async def get_by_id(cls: type['MediaAssetDao'], db: AsyncSession, asset_id: UUID) -> Optional[MediaAsset]:
        return await db.scalar(sa.select(MediaAsset).where(MediaAsset.id == asset_id))

    @classmethod
    async def mark_processing(cls: type['MediaAssetDao'], db: AsyncSession, asset: MediaAsset) -> MediaAsset:
        asset.processing_status = 'processing'
        asset.error_message = None
        await db.commit()
        await db.refresh(asset)
        return asset

    @classmethod
    async def mark_completed(
        cls: type['MediaAssetDao'],
        db: AsyncSession,
        asset: MediaAsset,
        transcript: Optional[str],
        description: Optional[str],
    ) -> MediaAsset:
        asset.processing_status = 'completed'
        asset.transcript = transcript
        asset.description = description
        asset.error_message = None
        await db.commit()
        await db.refresh(asset)
        return asset

    @classmethod
    async def mark_failed(cls: type['MediaAssetDao'], db: AsyncSession, asset: MediaAsset, error_message: str) -> MediaAsset:
        asset.processing_status = 'failed'
        asset.error_message = error_message[:2000]
        await db.commit()
        await db.refresh(asset)
        return asset
