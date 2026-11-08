import logging
from typing import Awaitable, Callable

from .async_opaca_client import AsyncOpacaClient, Timeout, TimeoutType
from ..keycloak_utils import KeycloakToken


log = logging.getLogger(__name__)


class ContainerPlatformClient(AsyncOpacaClient):
    """
    This client is intended to be used by containers to contact their parent platform.
    For the general async-client to contact OPACA platforms, see the AsyncOpacaClient class.
    """

    def __init__(
            self,
            url: str | None = None,
            token_provider: Callable[[], Awaitable[KeycloakToken]] | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> None:
        super().__init__(url, timeout)
        self._token_provider = token_provider

    async def platform_login(self, username: str, password: str, timeout: TimeoutType = Timeout.NOT_SET,) -> str:
        raise RuntimeError('Not valid on this client.')

    async def platform_login_renew(self, timeout: TimeoutType = Timeout.NOT_SET) -> str:
        raise RuntimeError('Not valid on this client.')

    async def _renew_token(self, force: bool = False) -> None:
        """
        Renew the access token using the token_provider.
        Do nothing if the token is not yet expired, unless force=True.

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
