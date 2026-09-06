import httpx

from typing import Dict

from settings import config


class HttpClientFactory:
    @classmethod
    def get_httpx_proxy_client(cls: type['HttpClientFactory'], provider: str) -> httpx.Client:
        proxy_url = cls._get_proxy_url(provider)
        if proxy_url:
            return httpx.Client(timeout=45.0, proxy=proxy_url)
        return httpx.Client(timeout=45.0)

    @classmethod
    def get_requests_proxies(cls: type['HttpClientFactory'], provider: str) -> Dict[str, str]:
        proxy_url = cls._get_proxy_url(provider)
        if not proxy_url:
            return {}
        return {'http': proxy_url, 'https': proxy_url}

    @classmethod
    def _get_proxy_url(cls: type['HttpClientFactory'], provider: str) -> str:
        if provider == 'telegram':
            return config.telegram.proxy_url or ''
        if provider == 'gemini':
            return config.gemini.proxy_url or ''
        raise ValueError(f'Unknown HTTP provider: {provider}')
