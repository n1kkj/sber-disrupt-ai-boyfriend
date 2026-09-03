import asyncio
from typing import List, Dict

import requests

import settings


def _request_gemini(system_prompt: str, messages: List[Dict[str, str]]) -> str:
    if not settings.GEMINI_API_KEY:
        return 'Я рядом. Расскажи, что сейчас происходит у тебя?'
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent'
    contents = [{'role': 'user' if item['role'] == 'user' else 'model', 'parts': [{'text': item['content']}]} for item in messages]
    response = requests.post(
        url,
        params={'key': settings.GEMINI_API_KEY},
        json={'system_instruction': {'parts': [{'text': system_prompt}]}, 'contents': contents},
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    return data['candidates'][0]['content']['parts'][0]['text']


async def generate_reply(system_prompt: str, messages: List[Dict[str, str]]) -> str:
    return await asyncio.to_thread(_request_gemini, system_prompt, messages)
