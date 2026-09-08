import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.logging import logger
from settings import config


class SecurityService:
    password_hash = PasswordHash.recommended()

    @classmethod
    def hash_password(cls: type['SecurityService'], password: str) -> str:
        return cls.password_hash.hash(password)

    @classmethod
    def verify_password(cls: type['SecurityService'], password: str, encoded: str) -> bool:
        if encoded.startswith('$argon2'):
            try:
                return cls.password_hash.verify(password, encoded)
            except (ValueError, TypeError):
                logger.warning('password_verification_failed reason=invalid_argon2_hash')
                return False
        result = cls._verify_legacy_password(password, encoded)
        if not result:
            logger.warning('password_verification_failed reason=invalid_legacy_hash')
        return result

    @classmethod
    def needs_password_rehash(cls: type['SecurityService'], encoded: str) -> bool:
        return not encoded.startswith('$argon2')

    @classmethod
    def _verify_legacy_password(cls: type['SecurityService'], password: str, encoded: str) -> bool:
        try:
            salt_text, digest_text = encoded.split('$', 1)
            salt = base64.urlsafe_b64decode(salt_text.encode())
            expected = base64.urlsafe_b64decode(digest_text.encode())
        except (ValueError, UnicodeDecodeError):
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 120000)
        return hmac.compare_digest(actual, expected)

    @classmethod
    def create_access_token(cls: type['SecurityService'], user_id: str) -> str:
        payload: Dict[str, Any] = {
            'sub': user_id,
            'exp': datetime.now(timezone.utc) + timedelta(minutes=config.auth.expire_minutes),
        }
        return jwt.encode(payload, config.auth.secret, algorithm='HS256')

    @classmethod
    def decode_access_token(cls: type['SecurityService'], token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, config.auth.secret, algorithms=['HS256'])
        except InvalidTokenError as error:
            logger.warning('access_token_decode_failed')
            raise ValueError('invalid token') from error
        if not payload.get('sub'):
            logger.warning('access_token_decode_failed reason=subject_missing')
            raise ValueError('invalid token')
        return payload
