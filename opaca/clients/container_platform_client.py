import asyncio
import logging
import httpx
from typing import Awaitable, Callable, Any, AsyncIterator
from httpx import QueryParams

from .async_opaca_client import AsyncOpacaClient, Timeout, TimeoutType
from ..keycloak_utils import KeycloakToken
from ..models import StreamContent


log = logging.getLogger(__name__)


class ContainerPlatformClient(AsyncOpacaClient):
    """
    This client is intended to be used by containers to contact their parent platform.
    For the general async-client to contact OPACA platforms, see the AsyncOpacaClient class.
    """

    def __init__(
            self,
            platform_url: str | None = None,
            token_provider: Callable[[], Awaitable[KeycloakToken]] | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> None:
        super().__init__(platform_url, timeout)
        self._token_provider = token_provider
        self._token_lock: asyncio.Lock = asyncio.Lock()

    async def platform_login(
            self,
            username: str,
            password: str,
            timeout: TimeoutType = Timeout.NOT_SET,
    ) -> str:
        raise RuntimeError('Not valid on this client.')

    async def renew_token(self, timeout: TimeoutType = Timeout.NOT_SET) -> str:
        raise RuntimeError('Not valid on this client.')

    async def _renew_token(self, force: bool = False) -> None:
        """
        Renew the access token using the token_provider.
        Do nothing if the token is not yet expired.

        :param force: Force renewal even if the token is not expired.
        """
        async with self._token_lock:
            if self._token_provider is None: return
            if not force and not self.access_token.is_expired(): return
            log.info('Renewing container access token...')
            try:
                self.access_token = await self._token_provider()
            except Exception as e:
                log.error(f'Failed to renew access token', exc_info=e)

    async def _request(
            self,
            method: str,
            path: str,
            body: Any | None = None,
            params: QueryParams | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> httpx.Response:
        """
        Check whether the access token is expired/close to expiring before sending the request,
        and also retry once in case of a 401.
        """
        if self.access_token.is_expired():
            await self._renew_token()
        try:
            return await super()._request(method, path, body, params, timeout)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401: await self._renew_token(force=True)
            else: raise e
        return await super()._request(method, path, body, params, timeout)

    async def _stream(
            self,
            method: str,
            path: str,
            content: StreamContent | None = None,
            params: QueryParams | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> AsyncIterator[bytes]:
        """
        Check whether the access token is expired/close to expiring before sending the request.
        No retry here, as the body-iterator might already be exhausted.
        """
        if self.access_token.is_expired():
            await self._renew_token()
        async for chunk in super()._stream(method, path, content, params, timeout):
            yield chunk