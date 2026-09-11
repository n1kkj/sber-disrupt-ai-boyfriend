import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.dao.chat_dao import ChatDao
from app.dao.media_asset_dao import MediaAssetDao
from app.dao.message_dao import MessageDao
from app.logging import logger
from app.models.media_asset import MediaAsset
from app.models.message import Message
from app.services.local_storage_service import LocalStorageService
from app.services.media_ai_service import GeminiMultimodalService
from app.services.media_probe_service import MediaProbeService
from app.services.redis_task_service import RedisTaskService
from settings import config


class MediaService:
    _allowed_types = {'audio', 'image', 'video'}

    @classmethod
    async def create_asset_message(
        cls: type['MediaService'],
        db: AsyncSession,
        user_id: UUID,
        chat_id: UUID,
        data: bytes,
        filename: str,
        mime_type: str,
        platform: str,
        external_id: Optional[str],
        message_type: str,
    ) -> Tuple[Message, MediaAsset, str]:
        if message_type not in cls._allowed_types:
            raise ValueError('Unsupported media type')
        cls._validate_size(message_type, len(data))
        if await ChatDao.get_with_boyfriend(db, user_id, chat_id) is None:
            raise LookupError('Chat not found')
        if external_id is not None:
            existing_message = await MessageDao.get_by_external_id(db, platform, external_id)
            if existing_message is not None:
                existing_assets = await MediaAssetDao.list_for_message(db, existing_message.id)
                if existing_assets:
                    return existing_message, existing_assets[0], RedisTaskService.get_task_id(str(existing_assets[0].id)) or ''
        message = await MessageDao.create(
            db,
            chat_id,
            'user',
            cls._placeholder(message_type),
            platform=platform,
            external_id=external_id,
            idempotency_key=external_id or str(uuid4()),
            message_type=message_type,
            status='processing',
        )
        suffix = Path(filename).suffix.lower() or cls._suffix_for_mime(mime_type)
        storage_key = await LocalStorageService.save_bytes(data, message.id, suffix)
        asset = await MediaAssetDao.create(
            db,
            message.id,
            platform,
            external_file_id=external_id,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=len(data),
        )
        await db.commit()
        await db.refresh(message)
        await db.refresh(asset)
        task_id = cls._dispatch_asset(asset.id, message_type)
        logger.info(
            'media_asset_created asset_id=%s message_id=%s type=%s bytes=%s task_id=%s',
            asset.id,
            message.id,
            message_type,
            len(data),
            task_id,
        )
        return message, asset, task_id

    @classmethod
    async def process_audio(cls: type['MediaService'], db: AsyncSession, asset_id: UUID) -> None:
        asset, message = await cls._get_asset_message(db, asset_id, 'audio')
        await MediaAssetDao.mark_processing(db, asset)
        try:
            path = LocalStorageService.get_path(asset.storage_key or '')
            duration = await MediaProbeService.duration_seconds(path)
            if duration > config.media.max_audio_duration_seconds:
                raise ValueError('Аудио превышает допустимую длительность')
            data = await LocalStorageService.read_bytes(asset.storage_key or '')
            transcript = await GeminiMultimodalService.transcribe_audio(data, asset.mime_type or 'audio/ogg')
            asset.duration_seconds = duration
            await MediaAssetDao.mark_completed(db, asset, transcript, None)
            message.content = transcript
            await cls._enqueue_message(db, message)
        except Exception as error:
            await cls._mark_failed(db, asset, message, error)
            raise

    @classmethod
    async def process_image(cls: type['MediaService'], db: AsyncSession, asset_id: UUID) -> None:
        asset, message = await cls._get_asset_message(db, asset_id, 'image')
        await MediaAssetDao.mark_processing(db, asset)
        try:
            data = await LocalStorageService.read_bytes(asset.storage_key or '')
            description = await GeminiMultimodalService.describe_image(data, asset.mime_type or 'image/jpeg')
            await MediaAssetDao.mark_completed(db, asset, None, description)
            message.content = f'[Изображение]\nОписание: {description}'
            await cls._enqueue_message(db, message)
        except Exception as error:
            await cls._mark_failed(db, asset, message, error)
            raise

    @classmethod
    async def process_video(cls: type['MediaService'], db: AsyncSession, asset_id: UUID) -> None:
        asset, message = await cls._get_asset_message(db, asset_id, 'video')
        await MediaAssetDao.mark_processing(db, asset)
        try:
            path = LocalStorageService.get_path(asset.storage_key or '')
            duration = await MediaProbeService.duration_seconds(path)
            if duration > config.media.max_video_duration_seconds:
                raise ValueError('Видео превышает допустимую длительность')
            frames, audio_data = await cls._extract_video_media(path)
            audio_transcript: Optional[str] = None
            if audio_data is not None:
                audio_transcript = await GeminiMultimodalService.transcribe_audio(audio_data, 'audio/wav')
            description = await GeminiMultimodalService.describe_video_frames(frames, audio_transcript)
            asset.duration_seconds = duration
            asset.metadata_json = {'frames_count': len(frames), 'frame_interval_seconds': config.media.video_frame_interval_seconds}
            await MediaAssetDao.mark_completed(db, asset, audio_transcript, description)
            content_parts = [f'[Видео]\nОписание: {description}']
            if audio_transcript:
                content_parts.append(f'Транскрипт аудио: {audio_transcript}')
            message.content = '\n'.join(content_parts)
            await cls._enqueue_message(db, message)
        except Exception as error:
            await cls._mark_failed(db, asset, message, error)
            raise

    @classmethod
    async def _get_asset_message(
        cls: type['MediaService'],
        db: AsyncSession,
        asset_id: UUID,
        expected_type: str,
    ) -> Tuple[MediaAsset, Message]:
        asset = await MediaAssetDao.get_by_id(db, asset_id)
        if asset is None:
            raise LookupError('Media asset not found')
        message = await MessageDao.get_by_id(db, asset.message_id)
        if message is None or message.message_type != expected_type:
            raise LookupError('Media message not found')
        return asset, message

    @classmethod
    async def _enqueue_message(cls: type['MediaService'], db: AsyncSession, message: Message) -> None:
        message.status = 'queued'
        await db.commit()
        task_id = str(uuid4())
        RedisTaskService.save_state(str(message.id), task_id, 'queued')
        from app.tasks.message_task import process_message_task

        process_message_task.apply_async(
            args=[str(message.id)],
            task_id=task_id,
            queue='messages',
        )
        logger.info('media_message_enqueued message_id=%s task_id=%s', message.id, task_id)

    @classmethod
    async def _mark_failed(
        cls: type['MediaService'],
        db: AsyncSession,
        asset: MediaAsset,
        message: Message,
        error: Exception,
    ) -> None:
        await MediaAssetDao.mark_failed(db, asset, str(error))
        message.status = 'failed'
        message.error_message = str(error)[:2000]
        await db.commit()
        logger.exception('media_processing_failed asset_id=%s message_id=%s', asset.id, message.id)

    @classmethod
    async def _extract_video_media(cls: type['MediaService'], path: Path) -> Tuple[List[bytes], Optional[bytes]]:
        return await asyncio.to_thread(cls._extract_video_media_sync, path)

    @classmethod
    def _extract_video_media_sync(cls: type['MediaService'], path: Path) -> Tuple[List[bytes], Optional[bytes]]:
        with tempfile.TemporaryDirectory(prefix='ai-companion-video-') as directory:
            directory_path = Path(directory)
            frames_path = directory_path / 'frame-%05d.jpg'
            fps = f'1/{config.media.video_frame_interval_seconds}'
            frame_command = [
                'ffmpeg', '-y', '-v', 'error', '-i', str(path), '-vf', f'fps={fps}',
                '-frames:v', str(config.media.video_max_frames), '-q:v', '4', str(frames_path),
            ]
            subprocess.run(frame_command, check=True, capture_output=True)
            frames = [frame.read_bytes() for frame in sorted(directory_path.glob('frame-*.jpg'))]
            audio_path = directory_path / 'audio.wav'
            audio_command = [
                'ffmpeg', '-y', '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', '16000',
                '-t', str(config.media.max_video_duration_seconds), str(audio_path),
            ]
            audio_result = subprocess.run(audio_command, capture_output=True)
            audio_data = audio_path.read_bytes() if audio_result.returncode == 0 and audio_path.exists() else None
            return frames, audio_data

    @classmethod
    def _dispatch_asset(cls: type['MediaService'], asset_id: UUID, message_type: str) -> str:
        task_id = str(uuid4())
        task_name = {
            'audio': 'app.tasks.media_task.ProcessAudioTask',
            'image': 'app.tasks.media_task.ProcessImageTask',
            'video': 'app.tasks.media_task.ProcessVideoTask',
        }[message_type]
        queue = message_type
        celery_app.send_task(task_name, args=[str(asset_id)], task_id=task_id, queue=queue)
        RedisTaskService.save_state(str(asset_id), task_id, 'queued')
        return task_id

    @classmethod
    def _validate_size(cls: type['MediaService'], message_type: str, size_bytes: int) -> None:
        limits = {
            'audio': config.media.max_audio_bytes,
            'image': config.media.max_image_bytes,
            'video': config.media.max_video_bytes,
        }
        if size_bytes > limits[message_type]:
            raise ValueError(f'Файл превышает лимит {limits[message_type] // 1024 // 1024} МБ')

    @classmethod
    def _placeholder(cls: type['MediaService'], message_type: str) -> str:
        return {'audio': '[Аудиосообщение обрабатывается]', 'image': '[Изображение обрабатывается]', 'video': '[Видео обрабатывается]'}[message_type]

    @classmethod
    def _suffix_for_mime(cls: type['MediaService'], mime_type: str) -> str:
        return {
            'audio/ogg': '.ogg',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'video/mp4': '.mp4',
            'video/webm': '.webm',
        }.get(mime_type, '.bin')
