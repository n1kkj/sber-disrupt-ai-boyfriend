from typing import List, Tuple
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Boyfriend, Chat, Message
from app.services.gemini import generate_reply
from app.services.memory import select_context


async def reply_to_message(
    db: AsyncSession,
    user_id: UUID,
    chat_id: UUID,
    content: str,
) -> Tuple[Message, Message]:
    chat_result = await db.execute(
        sa.select(Chat, Boyfriend).join(Boyfriend, Boyfriend.id == Chat.boyfriend_id).where(Chat.id == chat_id, Chat.user_id == user_id)
    )
    row = chat_result.first()
    if row is None:
        raise LookupError('Chat not found')
    chat, boyfriend = row
    history_result = await db.execute(sa.select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at.asc()))
    history = list(history_result.scalars())
    user_message = Message(chat_id=chat.id, role='user', content=content)
    db.add(user_message)
    await db.flush()
    context = select_context(history + [user_message], content)
    prompt_messages = [{'role': item.role, 'content': item.content} for item in context]
    reply = await generate_reply(boyfriend.system_prompt, prompt_messages)
    assistant_message = Message(chat_id=chat.id, role='assistant', content=reply)
    db.add(assistant_message)
    await db.commit()
    await db.refresh(user_message)
    await db.refresh(assistant_message)
    return user_message, assistant_message
