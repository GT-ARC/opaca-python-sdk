import logging
from typing import Tuple, Any, Dict, Annotated, Callable
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from keycloak import KeycloakOpenID
from jwcrypto.jwk import JWKSet, JWK

from opaca.models import TokenPair
from opaca.utils import http_error


log = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


class KeycloakClient:

    def __init__(self, keycloak_url: str, client_secret: str, container_id: str) -> None:
        self.keycloak_url = keycloak_url
        self.client_secret = client_secret
        self.container_id = container_id

        self._openid: KeycloakOpenID | None = None
        self._jwk_cache: JWKSet | None = None

    def _get_openid(self) -> KeycloakOpenID:
        if self._openid is not None:
            return self._openid

        if not self.keycloak_url:
            raise ValueError(f'Keycloak URL is not set: {self.keycloak_url}')

        url, realm = _split_keycloak_url_and_realm(self.keycloak_url)
        client: KeycloakOpenID = KeycloakOpenID(
            server_url=url,
            realm_name=realm,
            client_id=self.container_id,
            client_secret_key=self.client_secret
        )
        self._openid = client
        return client

    def _update_jwk_cache(self) -> None:
        if self._jwk_cache is not None: return
        keys = JWKSet()
        for cert in self._get_openid().certs()['keys']:
            jwk = JWK(**cert)
            keys.add(jwk)
        self._jwk_cache = keys

    def get_token_claims(self, token: str) -> Dict[str, Any]:
        """
        Decode the token and return the claims.

        leeway=10: Token expiry time can be exceeded by up to 10 seconds to account for clock inaccuracies.
        check_claims={'exp': None}: Token must have an expiry claim.
        """
        try:
            self._update_jwk_cache()
            claims = self._get_openid().decode_token(token, key=self._jwk_cache,
                 algs=['RS256'], leeway=10, check_claims={'exp': None})
        except Exception as e:
            raise ValueError('Failed to validate token') from e
        return claims

    def get_client_token(self) -> TokenPair:
        """
        Get an access token for an OPACA client.
        """
        try:
            data = self._get_openid().token(grant_type='client_credentials')
            return TokenPair.model_validate(data)
        except Exception as e:
            raise ValueError('Failed to get access token for client') from e


def create_token_dependency(client: KeycloakClient | None) -> Callable[[Any], Any]:
    """
    Create a FastAPI dependency to check the keycloak Bearer token, if present.
    """
    def check_header_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]) -> Dict[str, Any]:
        error_headers = {'WWW-Authenticate': 'Bearer'}
        if not client or not client.keycloak_url:
            return {}
        if credentials is None:
            raise http_error(401, cause='Missing Bearer token', headers=error_headers)

        try:
            token = credentials.credentials
            return client.get_token_claims(token)
        except Exception as e:
            raise http_error(401, cause='Failed to validate token', headers=error_headers) from e

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

