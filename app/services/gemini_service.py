from typing import Dict, List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.clients.http_client import HttpClientFactory
from app.logging import logger
from settings import config


class GeminiAIService:
    @classmethod
    def _validate_models(cls: type['GeminiAIService']) -> None:
        if config.gemini.model.startswith('gemini-embedding-'):
            raise ValueError('GEMINI_MODEL должен быть чат-моделью, а не embedding-моделью.')
        if config.gemini.embedding_model != 'gemini-embedding-001':
            raise ValueError('Для Gemini embeddings используйте GEMINI_EMBEDDING_MODEL=gemini-embedding-001.')

    @classmethod
    def get_chat_model(cls: type['GeminiAIService'], temperature: float = 0) -> ChatOpenAI:
        if not config.gemini.api_key:
            logger.error('gemini_chat_model_creation_failed reason=api_key_missing')
            raise ValueError('Не задан GEMINI_API_KEY для провайдера gemini.')
        cls._validate_models()
        return ChatOpenAI(
            model=config.gemini.model,
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
    async def generate_reply(cls: type['GeminiAIService'], system_prompt: str, messages: List[Dict[str, str]]) -> str:
        logger.info('gemini_request_started model=%s context_messages=%s', config.gemini.model, len(messages))
        try:
            chat_model = cls.get_chat_model()
            model_messages = [('system', system_prompt)] + [(item['role'], item['content']) for item in messages]
            response = await chat_model.ainvoke(model_messages)
            if isinstance(response.content, str):
                reply = response.content
            else:
                reply = ' '.join(str(part) for part in response.content)
            logger.info('gemini_request_completed model=%s response_chars=%s', config.gemini.model, len(reply))
            return reply
        except Exception:
            logger.exception('gemini_request_failed model=%s context_messages=%s', config.gemini.model, len(messages))
            raise
