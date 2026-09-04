import httpx


class HttpClientFactory:
    @classmethod
    def get_httpx_proxy_client(cls: type['HttpClientFactory'], provider: str) -> httpx.Client:
        return httpx.Client(timeout=45.0)
