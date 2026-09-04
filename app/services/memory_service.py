import re
from typing import List

from app.models.message import Message


class MemoryService:
    @classmethod
    def select_context(cls: type['MemoryService'], messages: List[Message], query: str, limit: int = 8) -> List[Message]:
        if not messages:
            return []
        query_words = set(re.findall(r'[a-zа-яё0-9]{3,}', query.lower()))
        scored = []
        for index, message in enumerate(messages):
            words = set(re.findall(r'[a-zа-яё0-9]{3,}', message.content.lower()))
            scored.append((len(query_words & words), index, message))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = {message.id: message for score, index, message in scored[:limit] if score > 0}
        for message in messages[-limit:]:
            selected[message.id] = message
        return sorted(selected.values(), key=lambda message: message.created_at)
