from typing import Dict, List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.clients.http_client import HttpClientFactory
from settings import config


class GeminiAIService:
    @classmethod
    def _validate_models(cls: type['GeminiAIService']) -> None:
        if config.gemini.MODEL.startswith('gemini-embedding-'):
            raise ValueError('GEMINI_MODEL должен быть чат-моделью (например gemini-2.5-pro), а не embedding-моделью.')
        if config.gemini.EMBEDDING_MODEL != 'gemini-embedding-001':
            raise ValueError('Для текущей OpenAI-совместимой интеграции Gemini embeddings используйте GEMINI_EMBEDDING_MODEL=gemini-embedding-001.')

    @classmethod
    def get_chat_model(cls: type['GeminiAIService'], temperature: float = 0) -> ChatOpenAI:
        if not config.gemini.API_KEY:
            raise ValueError('Не задан GEMINI_API_KEY для провайдера gemini.')
        cls._validate_models()
        return ChatOpenAI(
            model=config.gemini.MODEL,
            api_key=config.gemini.API_KEY,
            base_url=config.gemini.BASE_URL,
            temperature=temperature,
            http_client=HttpClientFactory.get_httpx_proxy_client('gemini'),
        )

    @classmethod
    def get_embeddings(cls: type['GeminiAIService']) -> OpenAIEmbeddings:
        if not config.gemini.API_KEY:
            raise ValueError('Не задан GEMINI_API_KEY для провайдера gemini.')
        cls._validate_models()
        return OpenAIEmbeddings(
            model=config.gemini.EMBEDDING_MODEL,
            api_key=config.gemini.API_KEY,
            base_url=config.gemini.BASE_URL,
            tiktoken_enabled=False,
            check_embedding_ctx_length=False,
            http_client=HttpClientFactory.get_httpx_proxy_client('gemini'),
        )

    @classmethod
    async def generate_reply(cls: type['GeminiAIService'], system_prompt: str, messages: List[Dict[str, str]]) -> str:
        chat_model = cls.get_chat_model()
        model_messages = [('system', system_prompt)] + [(item['role'], item['content']) for item in messages]
        response = await chat_model.ainvoke(model_messages)
        if isinstance(response.content, str):
            return response.content
        return ' '.join(str(part) for part in response.content)
