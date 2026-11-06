import httpx
import enum
from typing import Any, AsyncIterator, Callable, Awaitable
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
            platform_url: str | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> None:
        """
        A client for asynchronous interaction with an OPACA Runtime Platform.

        :param platform_url: The URL of the OPACA Runtime Platform.
        Leave as None for platforms without authentication.
        :param timeout: The default timeout for requests.
        """
        self.url: str | None = platform_url
        self.access_token: KeycloakToken | None = None
        self.refresh_token: KeycloakToken | None = None
        self.container_tokens: dict[str, str] = {}
        self.timeout: TimeoutType = None if timeout is Timeout.NOT_SET else timeout

    ### AUTHENTICATION ###

    async def platform_login(
            self,
            username: str,
            password: str,
            timeout: TimeoutType = Timeout.NOT_SET,
    ) -> str:
        """
        Acquire a login token from the platform. The token is also cached within
        the client itself and automatically added to all request headers.
        """
        self.access_token = None
        body = Login(username=username, password=password).model_dump(mode='json')
        response = await self._request('POST', '/login', body=body, timeout=timeout)
        tokens = TokenPair.model_validate(response.json())
        self.access_token = KeycloakToken(token=tokens.accessToken)
        self.refresh_token = KeycloakToken(token=tokens.refreshToken) if tokens.refreshToken else None
        return tokens.accessToken

    async def renew_token(self, timeout: TimeoutType = Timeout.NOT_SET) -> str:
        """
        Update the cached platform login token.
        """
        if self.refresh_token is None:
            raise ValueError(f'Cannot renew access token: refreshToken is missing. Call platform_login first.')
        body = TokenRenew(refreshToken=self.refresh_token.token).model_dump(mode='json')
        response = await self._request('POST', '/login/renew', body=body, timeout=timeout)
        tokens = TokenPair.model_validate(response.json())
        self.access_token = KeycloakToken(token=tokens.accessToken)
        self.refresh_token = KeycloakToken(token=tokens.refreshToken) if tokens.refreshToken else None
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
        if not self.url:
            raise UrlNotSetException(f'AsyncOpacaClient: Platform URL not set')
        timeout = self.timeout if timeout is Timeout.NOT_SET else timeout
        async with httpx.AsyncClient() as client:
            response = await client.request(method, f'{self.url}{path}', json=body, params=params, headers=self._headers(), timeout=timeout)
            response.raise_for_status()
            return response

    async def _stream(
            self,
            method: str,
            path: str,
            content: StreamContent | None = None,
            params: QueryParams | None = None,
            timeout: TimeoutType = Timeout.NOT_SET
    ) -> AsyncIterator[bytes]:
        if not self.url:
            raise UrlNotSetException(f'AsyncOpacaClient: Platform URL not set')
        timeout = self.timeout if timeout is Timeout.NOT_SET else timeout
        async with httpx.AsyncClient() as client:
            async with client.stream(method, f'{self.url}{path}', content=content, params=params, headers=self._headers(), timeout=timeout) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    yield chunk

    def _headers(self) -> dict[str, str] | None:
        headers = {'Content-Type': 'application/json; charset=UTF-8'}
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token.token}'
        return headers


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