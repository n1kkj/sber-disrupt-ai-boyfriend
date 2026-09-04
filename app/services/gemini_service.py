import asyncio
from typing import Dict, List

import requests

from settings import config


class GeminiService:
    @classmethod
    def _request(cls: type['GeminiService'], system_prompt: str, messages: List[Dict[str, str]]) -> str:
        if not config.gemini.api_key:
            return 'Я рядом. Расскажи, что сейчас происходит у тебя?'
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{config.gemini.model}:generateContent'
        contents = [{'role': 'user' if item['role'] == 'user' else 'model', 'parts': [{'text': item['content']}]} for item in messages]
        response = requests.post(url, params={'key': config.gemini.api_key}, json={'system_instruction': {'parts': [{'text': system_prompt}]}, 'contents': contents}, timeout=45)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text']

    @classmethod
    async def generate_reply(cls: type['GeminiService'], system_prompt: str, messages: List[Dict[str, str]]) -> str:
        return await asyncio.to_thread(cls._request, system_prompt, messages)
