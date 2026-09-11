import asyncio
from pathlib import Path
from uuid import UUID

from settings import config


class LocalStorageService:
    @classmethod
    async def save_bytes(cls: type['LocalStorageService'], data: bytes, asset_id: UUID, suffix: str) -> str:
        relative_key = f'{asset_id}/{asset_id}{suffix}'
        root = Path(config.media.storage_path).resolve()
        target = (root / relative_key).resolve()
        if root not in target.parents:
            raise ValueError('Invalid media storage path')
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_bytes, data)
        return relative_key

    @classmethod
    async def read_bytes(cls: type['LocalStorageService'], storage_key: str) -> bytes:
        root = Path(config.media.storage_path).resolve()
        target = (root / storage_key).resolve()
        if root not in target.parents:
            raise ValueError('Invalid media storage path')
        return await asyncio.to_thread(target.read_bytes)

    @classmethod
    def get_path(cls: type['LocalStorageService'], storage_key: str) -> Path:
        root = Path(config.media.storage_path).resolve()
        target = (root / storage_key).resolve()
        if root not in target.parents:
            raise ValueError('Invalid media storage path')
        return target
