import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any, Dict

from settings import config


class SecurityService:
    @classmethod
    def hash_password(cls: type['SecurityService'], password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 120000)
        return f'{cls._b64(salt)}${cls._b64(digest)}'

    @classmethod
    def verify_password(cls: type['SecurityService'], password: str, encoded: str) -> bool:
        try:
            salt_text, digest_text = encoded.split('$', 1)
            salt = base64.urlsafe_b64decode(salt_text.encode())
            expected = base64.urlsafe_b64decode(digest_text.encode())
        except (ValueError, UnicodeDecodeError):
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 120000)
        return hmac.compare_digest(actual, expected)

    @classmethod
    def _b64(cls: type['SecurityService'], value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b'=').decode()

    @classmethod
    def create_access_token(cls: type['SecurityService'], user_id: str) -> str:
        payload: Dict[str, Any] = {'sub': user_id, 'exp': int((datetime.now(UTC) + timedelta(minutes=config.auth.expire_minutes)).timestamp())}
        header = cls._b64(json.dumps({'alg': 'HS256', 'typ': 'JWT'}, separators=(',', ':')).encode())
        body = cls._b64(json.dumps(payload, separators=(',', ':')).encode())
        signature = cls._b64(hmac.new(config.auth.secret.encode(), f'{header}.{body}'.encode(), hashlib.sha256).digest())
        return f'{header}.{body}.{signature}'

    @classmethod
    def decode_access_token(cls: type['SecurityService'], token: str) -> Dict[str, Any]:
        try:
            header, body, signature = token.split('.')
            expected = cls._b64(hmac.new(config.auth.secret.encode(), f'{header}.{body}'.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                raise ValueError('invalid signature')
            padding = '=' * (-len(body) % 4)
            payload = json.loads(base64.urlsafe_b64decode(f'{body}{padding}'.encode()))
            if int(payload['exp']) < int(datetime.now(UTC).timestamp()):
                raise ValueError('expired token')
            return payload
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            raise ValueError('invalid token')
