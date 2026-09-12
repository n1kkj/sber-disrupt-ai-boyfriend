import asyncio
import json
import re
import secrets
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import requests
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.dao.boyfriend_dao import BoyfriendDao
from app.dao.chat_dao import ChatDao
from app.dao.user_dao import UserDao
from app.dao.onboarding_dao import OnboardingDao
from app.dao.user_profile_dao import UserProfileDao
from app.clients.http_client import HttpClientFactory
from app.logging import logger
from app.models.chat import Chat
from app.models.user import User
from app.security import SecurityService
from app.services.account_link_service import AccountLinkService
from app.services.message_service import MessageService
from app.services.media_service import MediaService
from app.services.onboarding_service import OnboardingService
from app.services.rate_limit_service import RateLimitService
from settings import config


class TelegramService:
    @classmethod
    async def get_or_create_chat(cls: type['TelegramService'], db: AsyncSession, telegram_id: int, username: Optional[str]) -> Chat:
        user = await UserDao.get_by_telegram_id(db, telegram_id)
        if user is None:
            user = await UserDao.create(
                db,
                f'telegram_{telegram_id}@local.invalid',
                SecurityService.hash_password(secrets.token_urlsafe(24)),
                username,
                telegram_id,
                True,
            )
            await UserProfileDao.ensure(db, user.id)
            await OnboardingDao.ensure(db, user.id)
            await db.commit()
            logger.info('telegram_only_user_created chat_suffix=%s', str(telegram_id)[-4:])
        chat = await ChatDao.get_for_platform(db, user.id, 'telegram')
        if chat is not None:
            return chat
        boyfriend = await BoyfriendDao.get_for_gender(db, 'male')
        if boyfriend is None:
            boyfriend = await BoyfriendDao.get_first_active(db)
        if boyfriend is None:
            raise RuntimeError('No active boyfriend configured')
        chat = await ChatDao.create(db, user.id, boyfriend.id, 'Telegram chat', 'telegram')
        return await ChatDao.commit(db, chat)

    @classmethod
    async def send_message(cls: type['TelegramService'], chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> None:
        if not config.telegram.bot_token:
            logger.warning('telegram_send_skipped reason=bot_token_missing')
            return
        logger.info('telegram_send_started chat_suffix=%s text_chars=%s', str(chat_id)[-4:], len(text))
        try:
            await asyncio.to_thread(cls._send_message, chat_id, text, reply_markup)
        except Exception:
            logger.exception('telegram_send_failed chat_suffix=%s', str(chat_id)[-4:])
            raise
        logger.info('telegram_send_completed chat_suffix=%s', str(chat_id)[-4:])

    @classmethod
    def _send_message(cls: type['TelegramService'], chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> None:
        payload: Dict[str, Any] = {'chat_id': chat_id, 'text': text}
        if reply_markup is not None:
            payload['reply_markup'] = reply_markup
        requests.post(f'https://api.telegram.org/bot{config.telegram.bot_token}/sendMessage', json=payload, proxies=HttpClientFactory.get_requests_proxies('telegram'), timeout=20).raise_for_status()

    @classmethod
    async def send_assistant_response(
        cls: type['TelegramService'],
        chat_id: int,
        assistant_message_id: UUID,
        text: str,
        telegram_connected: bool,
        send_audio: bool = False,
    ) -> None:
        await cls.send_message(chat_id, text, cls._connect_keyboard(telegram_connected))
        if send_audio:
            from app.tasks.speech_task import process_speech_task

            process_speech_task.apply_async(
                args=[str(assistant_message_id), chat_id, telegram_connected],
                queue='tts',
            )
            logger.info(
                'telegram_speech_enqueued chat_suffix=%s assistant_message_id=%s',
                str(chat_id)[-4:],
                assistant_message_id,
            )

    @classmethod
    async def send_voice(
        cls: type['TelegramService'],
        chat_id: int,
        audio: bytes,
        telegram_connected: bool,
    ) -> None:
        if not config.telegram.bot_token:
            logger.warning('telegram_voice_send_skipped reason=bot_token_missing')
            return
        logger.info('telegram_voice_send_started chat_suffix=%s bytes=%s', str(chat_id)[-4:], len(audio))
        try:
            await asyncio.to_thread(cls._send_voice, chat_id, audio, telegram_connected)
        except Exception:
            logger.exception('telegram_voice_send_failed chat_suffix=%s', str(chat_id)[-4:])
            raise
        logger.info('telegram_voice_send_completed chat_suffix=%s', str(chat_id)[-4:])

    @classmethod
    def _send_voice(
        cls: type['TelegramService'],
        chat_id: int,
        audio: bytes,
        telegram_connected: bool,
    ) -> None:
        response = requests.post(
            f'https://api.telegram.org/bot{config.telegram.bot_token}/sendVoice',
            data={
                'chat_id': str(chat_id),
                'reply_markup': json.dumps(cls._connect_keyboard(telegram_connected)),
            },
            files={'voice': ('response.ogg', audio, 'audio/ogg')},
            proxies=HttpClientFactory.get_requests_proxies('telegram'),
            timeout=60,
        )
        response.raise_for_status()

    @classmethod
    async def set_webhook(cls: type['TelegramService'], webhook_url: str) -> None:
        if not config.telegram.bot_token:
            raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured')
        logger.info('telegram_webhook_set_started')
        try:
            await asyncio.to_thread(cls._set_webhook, webhook_url)
        except Exception:
            logger.exception('telegram_webhook_set_failed')
            raise
        logger.info('telegram_webhook_set_completed')

    @classmethod
    async def delete_webhook(cls: type['TelegramService']) -> None:
        if not config.telegram.bot_token:
            raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured')
        logger.info('telegram_webhook_delete_started')
        try:
            await asyncio.to_thread(cls._delete_webhook)
        except Exception:
            logger.exception('telegram_webhook_delete_failed')
            raise
        logger.info('telegram_webhook_delete_completed')

    @classmethod
    async def process_update(cls: type['TelegramService'], db: AsyncSession, update: Dict[str, Any]) -> None:
        logger.info('telegram_update_received update_id=%s', update.get('update_id'))
        message = update.get('message') or update.get('edited_message')
        if not message or not message.get('chat', {}).get('id'):
            logger.debug('telegram_update_ignored reason=unsupported_payload')
            return
        telegram_chat_id = int(message['chat']['id'])
        telegram_user = message.get('from', {})
        text = str(message.get('text') or '')
        media_payload = cls._get_media_payload(message)
        if not text and media_payload is None:
            logger.debug('telegram_update_ignored reason=unsupported_payload')
            return
        username = telegram_user.get('username') or telegram_user.get('first_name')
        current_user = await UserDao.get_by_telegram_id(db, telegram_chat_id)
        is_platform_connected = current_user is not None and not current_user.is_telegram_only
        if text.startswith('/start'):
            payload = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) == 2 else ''
            if payload.startswith('link_'):
                try:
                    await AccountLinkService.claim_by_telegram(db, payload.removeprefix('link_'), telegram_chat_id)
                    logger.info('telegram_account_link_completed chat_suffix=%s', str(telegram_chat_id)[-4:])
                    await cls.send_message(telegram_chat_id, 'Telegram подключен к аккаунту платформы.', cls._connect_keyboard(True))
                except ValueError as error:
                    logger.warning('telegram_account_link_rejected chat_suffix=%s reason=%s', str(telegram_chat_id)[-4:], error)
                    await cls.send_message(telegram_chat_id, str(error), cls._connect_keyboard(is_platform_connected))
                return
            if is_platform_connected:
                chat = await cls.get_or_create_chat(db, telegram_chat_id, username)
                onboarding = await OnboardingService.start(db, chat.user_id)
                greeting = 'Привет! Я рядом.'
                await cls.send_message(telegram_chat_id, f'{greeting}\n\n{onboarding.question or "Онбординг завершен."}', cls._connect_keyboard(True))
            else:
                chat = await cls.get_or_create_chat(db, telegram_chat_id, username)
                onboarding = await OnboardingService.start(db, chat.user_id)
                await cls.send_message(telegram_chat_id, f'Привет! Я рядом.\n\n{onboarding.question or "Нажми кнопку, чтобы подключить Telegram к платформе."}', cls._connect_keyboard(False))
            return
        if text == 'Подключиться к платформе':
            if is_platform_connected:
                logger.info('telegram_account_link_skipped reason=already_connected chat_suffix=%s', str(telegram_chat_id)[-4:])
                await cls.send_message(telegram_chat_id, 'Telegram уже подключен к платформе.', cls._connect_keyboard(True))
                return
            logger.info('telegram_account_link_requested chat_suffix=%s', str(telegram_chat_id)[-4:])
            raw_token, expires_at = await AccountLinkService.create_for_telegram(db, telegram_chat_id)
            platform_url = f'{config.platform_url.rstrip("/")}/?telegram_link={raw_token}'
            await cls.send_message(telegram_chat_id, f'Открой ссылку и войди или зарегистрируйся на платформе. Ссылка действует до {expires_at:%H:%M}.\n\n{platform_url}', cls._connect_keyboard(False))
            return
        text, audio_requested = cls._extract_audio_command(text)
        if not text and media_payload is None:
            await cls.send_message(
                telegram_chat_id,
                'Напиши сообщение и добавь /audio, если нужен голосовой ответ.',
                cls._connect_keyboard(is_platform_connected),
            )
            return
        try:
            allowed, retry_after = await asyncio.to_thread(
                RateLimitService.consume,
                'telegram',
                str(telegram_chat_id),
            )
            if not allowed:
                logger.warning('telegram_message_rate_limited chat_suffix=%s retry_after=%s', str(telegram_chat_id)[-4:], retry_after)
                await cls.send_message(
                    telegram_chat_id,
                    'Слишком много сообщений подряд. Попробуй позже.',
                    cls._connect_keyboard(is_platform_connected),
                )
                return
            chat = await cls.get_or_create_chat(db, telegram_chat_id, username)
            onboarding = await OnboardingService.start(db, chat.user_id)
            if onboarding.status != 'completed':
                if not text:
                    await cls.send_message(
                        telegram_chat_id,
                        f'Сначала ответь текстом на вопрос onboarding:\n\n{onboarding.question}',
                        cls._connect_keyboard(is_platform_connected),
                    )
                    return
                try:
                    onboarding = await OnboardingService.answer(db, chat.user_id, text)
                except ValueError as error:
                    logger.info(
                        'telegram_onboarding_answer_invalid chat_suffix=%s step=%s reason=%s',
                        str(telegram_chat_id)[-4:],
                        onboarding.step,
                        error,
                    )
                    await cls.send_message(
                        telegram_chat_id,
                        f'{error}\n\n{onboarding.question}',
                        cls._connect_keyboard(is_platform_connected),
                    )
                    return
                await cls.send_message(
                    telegram_chat_id,
                    onboarding.question or 'Онбординг завершен. Теперь можно общаться.',
                    cls._connect_keyboard(is_platform_connected),
                )
                return
            if media_payload is not None:
                file_id, mime_type, filename, message_type = media_payload
                media_limits = {
                    'audio': config.media.max_audio_bytes,
                    'image': config.media.max_image_bytes,
                    'video': config.media.max_video_bytes,
                }
                media_data = await asyncio.to_thread(cls._download_file, file_id, media_limits[message_type])
                _, _, task_id = await MediaService.create_asset_message(
                    db,
                    chat.user_id,
                    chat.id,
                    media_data,
                    filename,
                    mime_type,
                    'telegram',
                    f'{telegram_chat_id}:{message["message_id"]}' if message.get('message_id') is not None else None,
                    message_type,
                )
                logger.info(
                    'telegram_media_enqueued chat_suffix=%s type=%s task_id=%s',
                    str(telegram_chat_id)[-4:],
                    message_type,
                    task_id,
                )
                return
            update_id = str(update.get('update_id')) if update.get('update_id') is not None else None
            external_id = (
                f'{telegram_chat_id}:{message["message_id"]}'
                if message.get('message_id') is not None
                else None
            )
            _, answer, _, is_new = await MessageService.enqueue_text(
                db,
                chat.user_id,
                chat.id,
                text,
                platform='telegram',
                external_id=external_id,
                idempotency_key=f'telegram:{update_id}' if update_id is not None else None,
                message_type='audio_request' if audio_requested else 'text',
            )
            if answer is not None and is_new:
                await cls.send_assistant_response(
                    telegram_chat_id,
                    answer.id,
                    answer.content,
                    is_platform_connected,
                )
        except Exception:
            logger.exception('telegram_update_processing_failed chat_suffix=%s update_id=%s', str(telegram_chat_id)[-4:], update.get('update_id'))
            await db.rollback()
            await cls.send_message(telegram_chat_id, 'Не получилось ответить. Попробуй еще раз через минуту.', cls._connect_keyboard(is_platform_connected))

    @classmethod
    def _connect_keyboard(cls: type['TelegramService'], connected: bool = False) -> Dict[str, Any]:
        if connected:
            return {'remove_keyboard': True}
        return {'keyboard': [[{'text': 'Подключиться к платформе'}]], 'resize_keyboard': True, 'is_persistent': True}

    @classmethod
    def _extract_audio_command(cls: type['TelegramService'], text: str) -> Tuple[str, bool]:
        pattern = r'(?<!\S)/audio(?!\S)'
        audio_requested = re.search(pattern, text, flags=re.IGNORECASE) is not None
        clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        return clean_text, audio_requested

    @classmethod
    def _get_media_payload(
        cls: type['TelegramService'],
        message: Dict[str, Any],
    ) -> Optional[tuple[str, str, str, str]]:
        voice = message.get('voice')
        if voice is not None:
            return str(voice['file_id']), str(voice.get('mime_type') or 'audio/ogg'), 'voice.ogg', 'audio'
        audio = message.get('audio')
        if audio is not None:
            return str(audio['file_id']), str(audio.get('mime_type') or 'audio/mpeg'), str(audio.get('file_name') or 'audio'), 'audio'
        video = message.get('video')
        if video is not None:
            return str(video['file_id']), str(video.get('mime_type') or 'video/mp4'), str(video.get('file_name') or 'video.mp4'), 'video'
        photo = message.get('photo')
        if photo:
            image = photo[-1]
            return str(image['file_id']), 'image/jpeg', 'photo.jpg', 'image'
        document = message.get('document')
        if document is not None:
            mime_type = str(document.get('mime_type') or '')
            if mime_type.startswith('audio/'):
                message_type = 'audio'
            elif mime_type.startswith('image/'):
                message_type = 'image'
            elif mime_type.startswith('video/'):
                message_type = 'video'
            else:
                return None
            return str(document['file_id']), mime_type, str(document.get('file_name') or 'document'), message_type
        return None

    @classmethod
    def _download_file(cls: type['TelegramService'], file_id: str, max_size_bytes: int) -> bytes:
        file_response = requests.get(
            f'https://api.telegram.org/bot{config.telegram.bot_token}/getFile',
            params={'file_id': file_id},
            proxies=HttpClientFactory.get_requests_proxies('telegram'),
            timeout=20,
        )
        file_response.raise_for_status()
        file_path = file_response.json().get('result', {}).get('file_path')
        if not file_path:
            raise RuntimeError('Telegram file path is missing')
        file_size = file_response.json().get('result', {}).get('file_size')
        if file_size is not None and int(file_size) > max_size_bytes:
            raise ValueError('Файл превышает допустимый размер')
        content_response = requests.get(
            f'https://api.telegram.org/file/bot{config.telegram.bot_token}/{file_path}',
            proxies=HttpClientFactory.get_requests_proxies('telegram'),
            timeout=60,
        )
        content_response.raise_for_status()
        return content_response.content

    @classmethod
    async def polling_loop(cls: type['TelegramService'], session_factory: async_sessionmaker, stop_event: asyncio.Event) -> None:
        offset = 0
        webhook_deleted = False
        logger.info('telegram_polling_loop_started')
        while not stop_event.is_set():
            try:
                if not webhook_deleted:
                    await cls.delete_webhook()
                    webhook_deleted = True
                updates = await asyncio.to_thread(cls._get_updates, offset)
                for update in updates:
                    offset = max(offset, int(update['update_id']) + 1)
                    async with session_factory() as session:
                        await cls.process_update(session, update)
            except asyncio.CancelledError:
                logger.info('telegram_polling_loop_cancelled')
                raise
            except Exception:
                logger.exception('telegram_polling_loop_failed offset=%s', offset)
                await asyncio.sleep(3)
        logger.info('telegram_polling_loop_finished')

    @classmethod
    def _set_webhook(cls: type['TelegramService'], webhook_url: str) -> None:
        payload = {'url': webhook_url}
        if config.telegram.webhook_secret:
            payload['secret_token'] = config.telegram.webhook_secret
        requests.post(f'https://api.telegram.org/bot{config.telegram.bot_token}/setWebhook', json=payload, proxies=HttpClientFactory.get_requests_proxies('telegram'), timeout=20).raise_for_status()

    @classmethod
    def _delete_webhook(cls: type['TelegramService']) -> None:
        requests.post(f'https://api.telegram.org/bot{config.telegram.bot_token}/deleteWebhook', proxies=HttpClientFactory.get_requests_proxies('telegram'), timeout=20).raise_for_status()

    @classmethod
    def _get_updates(cls: type['TelegramService'], offset: int) -> List[Dict[str, Any]]:
        response = requests.get(
            f'https://api.telegram.org/bot{config.telegram.bot_token}/getUpdates',
            params={
                'offset': offset,
                'timeout': config.telegram.polling_timeout,
                'allowed_updates': json.dumps(['message', 'edited_message']),
            },
            proxies=HttpClientFactory.get_requests_proxies('telegram'),
            timeout=config.telegram.polling_timeout + 10,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get('ok'):
            raise RuntimeError(f'Telegram getUpdates failed: {data}')
        return data.get('result', [])
