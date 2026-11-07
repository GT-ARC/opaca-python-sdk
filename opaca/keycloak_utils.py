import logging
import json
from typing import Tuple, Any, Dict, Annotated, Callable, TYPE_CHECKING, Awaitable
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from keycloak import KeycloakOpenID
from jwcrypto.jwk import JWKSet, JWK
from jwcrypto.common import base64url_decode
from datetime import datetime, UTC, timedelta

from pydantic import BaseModel

from .utils import http_error

if TYPE_CHECKING:
    from opaca import Container


log = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)
_EXPIRATION_OFFSET: timedelta = timedelta(seconds=30)

class KeycloakToken(BaseModel):
    token: str = ''
    expires_at: datetime | None = None

    @classmethod
    def from_jwt(cls, token: str) -> 'KeycloakToken':
        try:
            _, payload, _ = token.split('.')
            claims = json.loads(base64url_decode(payload))
            expires_at = datetime.fromtimestamp(claims['exp'], tz=UTC) if 'exp' in claims else None
            return cls(token=token, expires_at=expires_at)
        except Exception as e:
            log.warning(f'Failed to decode JWT: {e}')
            return cls(token=token)

    def is_expired(self) -> bool:
        if not self.expires_at: return True
        return (datetime.now(tz=UTC) + _EXPIRATION_OFFSET) > self.expires_at

    def clear(self) -> None:
        self.token = ''
        self.expires_at = None


class KeycloakClient:

    def __init__(self, keycloak_url: str, client_secret: str, client_id: str) -> None:
        self.keycloak_url = keycloak_url
        self.client_secret = client_secret
        self.client_id = client_id

        self._openid: KeycloakOpenID | None = None
        self._jwk_cache: JWKSet | None = None

    async def _get_openid(self) -> KeycloakOpenID:
        if self._openid is not None:
            return self._openid

        if not self.keycloak_url:
            raise ValueError(f'Keycloak URL is not set: {self.keycloak_url}')

        url, realm = _split_keycloak_url_and_realm(self.keycloak_url)
        client: KeycloakOpenID = KeycloakOpenID(
            server_url=url,
            realm_name=realm,
            client_id=self.client_id,
            client_secret_key=self.client_secret
        )
        self._openid = client
        return client

    async def _update_jwk_cache(self) -> None:
        if self._jwk_cache is not None: return
        keys = JWKSet()
        openid = await self._get_openid()
        for cert in (await openid.a_certs())['keys']:
            jwk = JWK(**cert)
            keys.add(jwk)
        self._jwk_cache = keys

    async def get_token_claims(self, token: str) -> Dict[str, Any]:
        """
        Decode the token and return the claims.

        leeway=10: Token expiry time can be exceeded by up to 10 seconds to account for clock inaccuracies.
        check_claims={'exp': None}: Token must have an expiry claim.
        """
        try:
            await self._update_jwk_cache()
            openid = await self._get_openid()
            claims = await openid.a_decode_token(token, key=self._jwk_cache,
                 algs=['RS256'], leeway=10, check_claims={'exp': None})
        except Exception as e:
            raise ValueError('Failed to validate token') from e
        return claims

    async def get_client_token(self) -> KeycloakToken:
        """
        Get an access token for an OPACA client.
        """
        try:
            openid = await self._get_openid()
            data = await openid.a_token(grant_type='client_credentials')
            return KeycloakToken(
                token=data['access_token'],
                expires_at=datetime.now(tz=UTC) + timedelta(seconds=data['expires_in'])
            )
        except Exception as e:
            raise ValueError('Failed to get access token for client') from e


def create_token_dependency(container: 'Container') -> Callable[[Any], Awaitable[Any]]:
    """
    Create a FastAPI dependency to check the keycloak Bearer token, if present.
    """
    keycloak_client = container.keycloak_client

    async def check_header_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]) -> Dict[str, Any]:
        error_headers = {'WWW-Authenticate': 'Bearer'}
        if not keycloak_client or not keycloak_client.keycloak_url:
            return {}
        if credentials is None:
            raise http_error(401, cause='Missing Bearer token', headers=error_headers)

        try:
            token = credentials.credentials
            claims = await keycloak_client.get_token_claims(token)
        except Exception as e:
            raise http_error(401, cause='Failed to validate token', headers=error_headers) from e

        client_id = claims.get('client_id') or claims.get('azp')
        if not isinstance(client_id, str) or not await container.check_client_id(client_id):
            raise http_error(401, cause='Failed to validate client_id', headers=error_headers)

        return claims

    return check_header_token


def _split_keycloak_url_and_realm(url_and_realm: str) -> Tuple[str, str]:
    try:
        split = url_and_realm.split('/realms/', maxsplit=1)
        url = split[0]
        realm = split[1].strip('/')
        return url, realm
    except IndexError as e:
        log.error(f'Keycloak URL needs to include the realm: {url_and_realm}')
        raise e

