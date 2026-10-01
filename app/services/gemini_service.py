import re
from typing import Dict, List, Optional, Type, TypeVar

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel

from app.clients.http_client import HttpClientFactory
from app.logging import logger
from app.services.gemini_rate_limiter import GeminiRateLimiter
from settings import config


SchemaType = TypeVar('SchemaType', bound=BaseModel)


class GeminiAIService:
    @classmethod
    def _validate_models(cls: type['GeminiAIService'], chat_model: Optional[str] = None) -> None:
        selected_model = chat_model or config.gemini.model
        if selected_model.startswith('gemini-embedding-'):
            raise ValueError('Чат-модель не может быть embedding-моделью.')
        if config.gemini.embedding_model != 'gemini-embedding-001':
            raise ValueError('Для Gemini embeddings используйте GEMINI_EMBEDDING_MODEL=gemini-embedding-001.')

    @classmethod
    def get_chat_model(
        cls: type['GeminiAIService'],
        temperature: float = 0,
        model: Optional[str] = None,
    ) -> ChatOpenAI:
        if not config.gemini.api_key:
            logger.error('gemini_chat_model_creation_failed reason=api_key_missing')
            raise ValueError('Не задан GEMINI_API_KEY для провайдера gemini.')
        selected_model = model or config.gemini.model
        cls._validate_models(selected_model)
        return ChatOpenAI(
            model=selected_model,
            api_key=config.gemini.api_key,
            base_url=config.gemini.base_url,
            temperature=temperature,
            http_client=HttpClientFactory.get_httpx_proxy_client('gemini'),
            http_async_client=HttpClientFactory.get_httpx_async_proxy_client('gemini'),
        )

    @classmethod
    def get_embeddings(cls: type['GeminiAIService']) -> OpenAIEmbeddings:
        if not config.gemini.api_key:
            logger.error('gemini_embeddings_creation_failed reason=api_key_missing')
            raise ValueError('Не задан GEMINI_API_KEY для провайдера gemini.')
        cls._validate_models()
        return OpenAIEmbeddings(
            model=config.gemini.embedding_model,
            api_key=config.gemini.api_key,
            base_url=config.gemini.base_url,
            tiktoken_enabled=False,
            check_embedding_ctx_length=False,
            http_client=HttpClientFactory.get_httpx_proxy_client('gemini'),
            http_async_client=HttpClientFactory.get_httpx_async_proxy_client('gemini'),
        )

    @classmethod
    async def generate_reply(
        cls: type['GeminiAIService'],
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0,
    ) -> str:
        selected_model = model or config.gemini.model
        logger.info('gemini_request_started model=%s context_messages=%s', selected_model, len(messages))
        try:
            await GeminiRateLimiter.acquire_async()
            chat_model = cls.get_chat_model(temperature=temperature, model=selected_model)
            model_messages = [('system', system_prompt)] + [(item['role'], item['content']) for item in messages]
            response = await chat_model.ainvoke(model_messages)
            if isinstance(response.content, str):
                reply = response.content
            else:
                reply = ' '.join(str(part) for part in response.content)
            reply = reply.strip()
            if not reply:
                raise ValueError('Gemini вернул пустой текстовый ответ')
            logger.info('gemini_request_completed model=%s response_chars=%s', selected_model, len(reply))
            return reply
        except Exception:
            logger.exception('gemini_request_failed model=%s context_messages=%s', selected_model, len(messages))
            raise

    @classmethod
    async def generate_json(
        cls: type['GeminiAIService'],
        system_prompt: str,
        messages: List[Dict[str, str]],
        schema: Type[SchemaType],
        model: Optional[str] = None,
    ) -> SchemaType:
        raw_result = await cls.generate_reply(
            system_prompt,
            messages,
            model=model,
            temperature=0,
        )
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw_result.strip(), flags=re.IGNORECASE)
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start >= 0 and end >= start:
            cleaned = cleaned[start:end + 1]
        return schema.model_validate_json(cleaned)
