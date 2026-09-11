from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import current_user
from app.dto.media import MediaTaskResponse
from app.logging import logger
from app.models.user import User
from app.services.media_service import MediaService
from settings import config


router = APIRouter(tags=['media'])


@router.post('/chats/{chat_id}/media', response_model=MediaTaskResponse, status_code=202)
async def upload_media(
    chat_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> MediaTaskResponse:
    mime_type = file.content_type or 'application/octet-stream'
    if mime_type.startswith('audio/'):
        message_type = 'audio'
    elif mime_type.startswith('image/'):
        message_type = 'image'
    elif mime_type.startswith('video/'):
        message_type = 'video'
    else:
        raise HTTPException(status_code=415, detail='Поддерживаются audio, image и video файлы')
    limits = {
        'audio': config.media.max_audio_bytes,
        'image': config.media.max_image_bytes,
        'video': config.media.max_video_bytes,
    }
    if file.size is not None and file.size > limits[message_type]:
        raise HTTPException(status_code=413, detail='Файл превышает допустимый размер')
    chunks = []
    total_size = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > limits[message_type]:
            raise HTTPException(status_code=413, detail='Файл превышает допустимый размер')
        chunks.append(chunk)
    data = b''.join(chunks)
    logger.info('media_upload_started user_id=%s chat_id=%s type=%s bytes=%s', user.id, chat_id, message_type, len(data))
    try:
        message, asset, task_id = await MediaService.create_asset_message(
            db,
            user.id,
            chat_id,
            data,
            file.filename or 'upload',
            mime_type,
            'web',
            None,
            message_type,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=413, detail=str(error))
    return MediaTaskResponse(
        message=message,
        asset_id=asset.id,
        task_id=task_id,
        processing_status=asset.processing_status,
    )
