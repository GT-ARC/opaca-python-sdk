import asyncio
import httpx
import enum
from typing import Any, AsyncIterator
from httpx import QueryParams

from ..keycloak_utils import KeycloakToken
from ..models import ContainerDescription, PlatformInfo, PostContainer, Login, AgentDescription, ConnectionRequest, \
    Message, Event, StreamContent, TokenPair, TokenRenew

class Timeout(enum.Enum):
    NOT_SET = enum.auto()


TimeoutType = float | int | Timeout | None


class AsyncOpacaClient:

    def __init__(
            self,
            url: str | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> None:
        """
        A client for asynchronous interaction with an OPACA Runtime Platform.

        :param url: The URL of the OPACA Runtime Platform.
        :param timeout: The default timeout for requests.
        """
        self.url: str | None = url
        self.access_token: KeycloakToken = KeycloakToken()
        self.refresh_token: KeycloakToken = KeycloakToken()
        self.container_tokens: dict[str, str] = {}
        self.timeout: TimeoutType = None if timeout is Timeout.NOT_SET else timeout
        self._token_lock: asyncio.Lock = asyncio.Lock()

    ### AUTHENTICATION ###

    async def platform_login(
            self,
            username: str,
            password: str,
            timeout: TimeoutType = Timeout.NOT_SET,
    ) -> str:
        """
        Acquire an access token from the platform. The token is also cached within
        the client itself and automatically added to all request headers.
        This also fetches a refresh token, which can be used to fetch a new access token
        by using the platform_login_renew() method.

        :return: The access token.
        """
        self.access_token = KeycloakToken()
        body = Login(username=username, password=password).model_dump(mode='json')
        response = await self._request_unsafe('POST', '/login', body=body, timeout=timeout)
        tokens = TokenPair.model_validate(response.json())
        self.access_token = KeycloakToken.from_jwt(tokens.accessToken)
        self.refresh_token = KeycloakToken.from_jwt(tokens.refreshToken) \
            if tokens.refreshToken else KeycloakToken()
        return tokens.accessToken

    async def platform_login_renew(self, timeout: TimeoutType = Timeout.NOT_SET) -> str:
        """
        Acquire a new access token from the platform by using the cached refresh token.

        :return: The new access token.
        """
        if not self.refresh_token:
            raise ValueError(f'Cannot renew access token: refreshToken is missing. Call platform_login first.')
        self.access_token = KeycloakToken()
        body = TokenRenew(refreshToken=self.refresh_token.token).model_dump(mode='json')
        response = await self._request_unsafe('POST', '/login/renew', body=body, timeout=timeout)
        tokens = TokenPair.model_validate(response.json())
        self.access_token = KeycloakToken.from_jwt(tokens.accessToken)
        self.refresh_token = KeycloakToken.from_jwt(tokens.refreshToken) \
            if tokens.refreshToken else KeycloakToken()
        return tokens.accessToken

    async def container_login(
            self,
            container_id: str,
            username: str,
            password: str,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> str:
        """
        Acquires a login token from a container. The token is also cached internally.
        """
        body = Login(username=username, password=password).model_dump(mode='json')
        response = await self._request('POST', f'/containers/login/{container_id}', body=body, timeout=timeout)
        token = response.text
        self.container_tokens[container_id] = token
        return token

    async def container_logout(self, container_id: str) -> bool:
        if container_id not in self.container_tokens: return False
        response = await self._request('POST', f'/containers/logout/{container_id}')
        del self.container_tokens[container_id]
        return response.json()

    ### CONTAINERS ###

    async def get_containers(
            self,
            include_connected: bool = False,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> list[ContainerDescription]:
        """
        Get a list of all containers. If includeConnected is True, also include containers from connected platforms.
        """
        params = _build_query_params(includeConnected=include_connected)
        response = await self._request('GET', '/containers', params=params, timeout=timeout)
        return [ContainerDescription.model_validate(container)
                for container in response.json()]

    async def post_container(
            self,
            post_container: PostContainer,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> str:
        body = post_container.model_dump(mode='json')
        response = await self._request('POST', '/containers', body=body, timeout=timeout)
        return response.text

    async def put_container(
            self,
            post_container: PostContainer,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> str:
        body = post_container.model_dump(mode='json')
        response = await self._request('PUT', '/containers', body=body, timeout=timeout)
        return response.text

    async def delete_container(
            self,
            container_id: str,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> bool:
        response = await self._request('DELETE', f'/containers/{container_id}', timeout=timeout)
        return response.json()

    async def post_container_notify(
            self,
            container_id: str,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> bool:
        response = await self._request('POST', f'/containers/notify', body=container_id, timeout=timeout)
        return response.json()

    ### AGENTS ###

    async def get_agents(
            self,
            include_connected: bool = False,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> list[AgentDescription]:
        """
        Get a list of all agents. If includeConnected is True, also include agents from connected platforms.
        """
        params = _build_query_params(includeConnected=include_connected)
        response = await self._request('GET', '/agents', params=params, timeout=timeout)
        return [AgentDescription.model_validate(agent) for agent in response.json()]

    async def get_agent(
            self,
            agent_id: str,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> AgentDescription:
        response = await self._request('GET', f'/agents/{agent_id}', timeout=timeout)
        return AgentDescription.model_validate(response.json())

    async def invoke(
            self,
            action: str,
            agent_id: str | None = None,
            args: dict[str, Any] | None = None,
            container_id: str | None = None,
            forward: bool = True,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> Any | None:
        if args is None:
            args = {}
        path = f'/invoke/{action}' + (f'/{agent_id}' if agent_id else '')
        params = _build_query_params(containerId=container_id, forward=forward)
        response = await self._request('POST', path, body=args, params=params, timeout=timeout)
        return response.json()

    async def get_stream(
            self,
            stream: str,
            agent_id: str | None = None,
            container_id: str | None = None,
            forward: bool = True,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> AsyncIterator[bytes]:
        """
        Returns an async iterator over a byte stream. You can collect the data
        using an ``async for`` loop.
        """
        path = f'/stream/{stream}' + (f'/{agent_id}' if agent_id else '')
        params = _build_query_params(containerId=container_id, forward=forward)
        async for chunk in self._stream('GET', path, params=params, timeout=timeout):
            yield chunk

    async def post_stream(
            self,
            stream: str,
            content: StreamContent | None = None,
            agent_id: str | None = None,
            container_id: str | None = None,
            forward: bool = True,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> AsyncIterator[bytes]:
        """
        The stream content that is posted can be any iterable byte stream data.

        Returns an async iterator over a byte stream. You can collect the data
        using an ``async for`` loop.
        """
        path = f'/stream/{stream}' + (f'/{agent_id}' if agent_id else '')
        params = _build_query_params(containerId=container_id, forward=forward)
        async for chunk in self._stream('POST', path, content=content, params=params, timeout=timeout):
            yield chunk

    ### CONNECTIONS ###

    async def get_connections(
            self,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> list[str]:
        response = await self._request('GET', '/connections', timeout=timeout)
        return response.json()

    async def post_connection(
            self,
            connection: str,
            connect_back: bool = False,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> bool:
        body = {'url': connection, 'connectBack': connect_back, 'token': None}
        response = await self._request('POST', '/connections', body=body, timeout=timeout)
        return response.json()

    async def delete_connection(
            self,
            connection: str,
            connect_back: bool = False,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> bool:
        body = ConnectionRequest(url=connection, connectBack=connect_back).model_dump(mode='json')
        response = await self._request('DELETE', f'/connections', body=body, timeout=timeout)
        return response.json()

    async def post_connection_notify(
            self,
            connection: str,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> bool:
        response = await self._request('POST', '/connections/notify', body=connection, timeout=timeout)
        return response.json()

    ### MESSAGES ###

    async def send_message(
            self,
            agent_id: str,
            message: Message,
            container_id: str | None = None,
            forward: bool = True,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> None:
        body = message.model_dump(mode='json')
        params = _build_query_params(containerId=container_id, forward=forward)
        await self._request('POST', f'/send/{agent_id}', body=body, params=params, timeout=timeout)

    async def broadcast(
            self,
            channel: str,
            message: Message,
            container_id: str | None = None,
            forward: bool = True,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> None:
        body = message.model_dump(mode='json')
        params = _build_query_params(containerId=container_id, forward=forward)
        await self._request('POST', f'/broadcast/{channel}', body=body, params=params, timeout=timeout)

    ### INFO ###

    async def get_info(
            self,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> PlatformInfo:
        response = await self._request('GET', '/info', timeout=timeout)
        return PlatformInfo.model_validate(response.json())

    async def get_config(
            self,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> dict[str, Any]:
        response = await self._request('GET', '/config', timeout=timeout)
        return response.json()

    async def get_history(
            self,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> list[Event]:
        response = await self._request('GET', '/history', timeout=timeout)
        return [Event.model_validate(event) for event in response.json()]

    ### PRIVATE HELPER METHODS ###

    async def _request(
            self,
            method: str,
            path: str,
            body: Any | None = None,
            params: QueryParams | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> httpx.Response:
        """
        Send a generic request to the platform.

        Check whether the access token is expired/close to expiring before sending the request,
        and also retry once in case of a 401.
        """
        if not self.url:
            raise UrlNotSetException(f'AsyncOpacaClient: Platform URL not set')
        timeout = self.timeout if timeout is Timeout.NOT_SET else timeout
        url = f'{self.url}{path}'
        if self.access_token.is_expired():
            await self._renew_token()
        try:
            return await _httpx_request(method, url, body, params, self._headers(), timeout)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401: await self._renew_token(force=True)
            else: raise e
        return await _httpx_request(method, url, body, params, self._headers(), timeout)

    async def _request_unsafe(
            self,
            method: str,
            path: str,
            body: Any | None = None,
            params: QueryParams | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> httpx.Response:
        """
        Send a generic request to the platform.

        This variant does not check whether the access token is expired beforehand,
        and also does not attempt a retry after a failed request.
        This is used by the methods that explicitly do not want/need to renew the token,
        i.e. the platform-login methods.
        """
        if not self.url:
            raise UrlNotSetException(f'AsyncOpacaClient: Platform URL not set')
        timeout = self.timeout if timeout is Timeout.NOT_SET else timeout
        url = f'{self.url}{path}'
        return await _httpx_request(method, url, body, params, self._headers(), timeout)

    async def _stream(
            self,
            method: str,
            path: str,
            content: StreamContent | None = None,
            params: QueryParams | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> AsyncIterator[bytes]:
        """
        Send a generic streaming request to the platform.

        Check whether the access token is expired/close to expiring before sending the request.
        No retry in case of 401, as the body-iterator might already be exhausted.
        """
        if not self.url:
            raise UrlNotSetException(f'AsyncOpacaClient: Platform URL not set')
        timeout = self.timeout if timeout is Timeout.NOT_SET else timeout
        url = f'{self.url}{path}'
        if self.access_token.is_expired():
            await self._renew_token()
        async for chunk in _httpx_stream(method, url, content, params, self._headers(), timeout):
            yield chunk

    def _headers(self) -> dict[str, str] | None:
        headers = {'Content-Type': 'application/json; charset=UTF-8'}
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token.token}'
        return headers

    async def _renew_token(self, force: bool = False) -> None:
        if not self.refresh_token: return
        async with self._token_lock:
            if force or self.access_token.is_expired():
                await self.platform_login_renew(timeout=30)


async def _httpx_request(
        method: str,
        url: str,
        body: Any | None = None,
        params: QueryParams | None = None,
        headers: dict[str, str] | None = None,
        timeout: TimeoutType = None,
) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, json=body, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response


async def _httpx_stream(
        method: str,
        url: str,
        content: StreamContent | None = None,
        params: QueryParams | None = None,
        headers: dict[str, str] | None = None,
        timeout: TimeoutType = None,
) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient() as client:
        async with client.stream(method, url, content=content, params=params, headers=headers, timeout=timeout) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk


def _build_query_params(**kwargs) -> QueryParams | None:
    filtered_params = {
        param: value
        for param, value in kwargs.items()
        if value is not None
    }
    if len(filtered_params) == 0:
        return None
    return QueryParams(**filtered_params)


class UrlNotSetException(ValueError):
    pass