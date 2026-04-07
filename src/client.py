import httpx
from typing import Any, AsyncIterator, Iterable, AsyncIterable
from httpx import QueryParams

from .models import ContainerDescription, PlatformInfo, PostContainer, Login, AgentDescription, ConnectionRequest, \
    Message, Event, StreamContent


class AsyncOpacaClient:

    def __init__(self, url: str):
        self.url: str = url
        self.token: str | None = None
        self.container_tokens: dict[str, str] = {}

    ### AUTHENTICATION ###

    async def platform_login(self, username: str, password: str) -> None:
        """
        Acquire a login token from the platform. The token is also cached within
        the client itself and automatically added to all request headers.
        """
        body = Login(username=username, password=password).model_dump(mode='json')
        response = await self._request('POST', '/login', body=body)
        self.token = response.text
        return self.token

    async def renew_token(self) -> None:
        """
        Update the cached platform login token.
        """
        response = await self._request('GET', '/token')
        self.token = response.text
        return self.token

    async def container_login(self, container_id: str, username: str, password: str) -> str:
        """
        Acquires a login token from a container. The token is also cached internally.
        """
        body = Login(username=username, password=password).model_dump(mode='json')
        response = await self._request('POST', f'/containers/login/{container_id}', body=body)
        self.container_tokens[container_id] = response.text
        return self.container_tokens[container_id]

    async def container_logout(self, container_id: str) -> bool:
        if container_id not in self.container_tokens: return False
        response = await self._request('POST', f'/containers/logout/{container_id}')
        del self.container_tokens[container_id]
        return response.json()

    ### CONTAINERS ###

    async def get_containers(self) -> list[ContainerDescription]:
        response = await self._request('GET', '/containers')
        return [ContainerDescription.model_validate(container)
                for container in response.json()]

    async def post_container(self, post_container: PostContainer) -> str:
        body = post_container.model_dump(mode='json')
        response = await self._request('POST', '/containers', body=body)
        return response.text

    async def put_container(self, post_container: PostContainer) -> str:
        body = post_container.model_dump(mode='json')
        response = await self._request('PUT', '/containers', body=body)
        return response.text

    async def delete_container(self, container_id: str) -> bool:
        response = await self._request('DELETE', f'/containers/{container_id}')
        return response.json()

    async def post_container_notify(self, container_id: str) -> bool:
        response = await self._request('POST', f'/containers/notify', body=container_id)
        return response.json()

    ### AGENTS ###

    async def get_agents(self) -> list[AgentDescription]:
        response = await self._request('GET', '/agents')
        return [AgentDescription.model_validate(agent) for agent in response.json()]

    async def get_agent(self, agent_id: str) -> AgentDescription:
        response = await self._request('GET', f'/agents/{agent_id}')
        return AgentDescription.model_validate(response.json())

    async def invoke(
            self,
            action: str,
            agent_id: str | None = None,
            args: dict[str, Any] | None = None,
            container_id: str | None = None,
            forward: bool = True
    ) -> Any | None:
        if args is None:
            args = {}
        path = f'/invoke/{action}' + (f'/{agent_id}' if agent_id else '')
        params = _build_query_params(containerId=container_id, forward=forward)
        response = await self._request('POST', path, body=args, params=params)
        return response.json()

    async def get_stream(
            self,
            stream: str,
            agent_id: str | None = None,
            container_id: str | None = None,
            forward: bool = True
    ) -> AsyncIterator[bytes]:
        """
        Returns an async iterator over a byte stream. You can collect the data
        using an ``async for`` loop.
        """
        path = f'/stream/{stream}' + (f'/{agent_id}' if agent_id else '')
        params = _build_query_params(containerId=container_id, forward=forward)
        async for chunk in self._stream('GET', path, params=params):
            yield chunk

    async def post_stream(
            self,
            stream: str,
            content: StreamContent = None,
            agent_id: str | None = None,
            container_id: str | None = None,
            forward: bool = True
    ) -> AsyncIterator[bytes]:
        """
        The stream content that is posted can be any iterable byte stream data.

        Returns an async iterator over a byte stream. You can collect the data
        using an ``async for`` loop.
        """
        path = f'/stream/{stream}' + (f'/{agent_id}' if agent_id else '')
        params = _build_query_params(containerId=container_id, forward=forward)
        async for chunk in self._stream('POST', path, content=content, params=params):
            yield chunk

    ### CONNECTIONS ###

    async def get_connections(self) -> list[str]:
        response = await self._request('GET', '/connections')
        return response.json()

    async def post_connection(self, connection: str, connect_back: bool = False) -> bool:
        body = {'url': connection, 'connectBack': connect_back, 'token': None}
        response = await self._request('POST', '/connections', body=body)
        return response.json()

    async def delete_connection(self, connection: str, connect_back: bool = False) -> bool:
        body = ConnectionRequest(url=connection, connectBack=connect_back).model_dump(mode='json')
        response = await self._request('DELETE', f'/connections', body=body)
        return response.json()

    async def post_connection_notify(self, connection: str) -> bool:
        response = await self._request('POST', '/connections/notify', body=connection)
        return response.json()

    ### MESSAGES ###

    async def send_message(self, agent_id: str, message: Message, container_id: str | None = None, forward: bool = True) -> None:
        body = message.model_dump(mode='json')
        params = _build_query_params(containerId=container_id, forward=forward)
        await self._request('POST', f'/send/{agent_id}', body=body, params=params)

    async def broadcast(self, channel: str, message: Message, container_id: str | None = None, forward: bool = True) -> None:
        body = message.model_dump(mode='json')
        params = _build_query_params(containerId=container_id, forward=forward)
        await self._request('POST', f'/broadcast/{channel}', body=body, params=params)

    ### INFO ###

    async def get_info(self) -> PlatformInfo:
        response = await self._request('GET', '/info')
        return PlatformInfo.model_validate(response.json())

    async def get_config(self) -> dict[str, Any]:
        response = await self._request('GET', '/config')
        return response.json()

    async def get_history(self) -> list[Event]:
        response = await self._request('GET', '/history')
        return [Event.model_validate(event) for event in response.json()]

    ### PRIVATE HELPER METHODS ###

    async def _request(self, method: str, path: str, body: Any | None = None, params: QueryParams | None = None, timeout: float = 10) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, f'{self.url}{path}', json=body, params=params, headers=self._headers(), timeout=timeout)
            response.raise_for_status()
            return response

    async def _stream(self, method: str, path: str, content: StreamContent = None, params: QueryParams | None = None, timeout: float = 10) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient() as client:
            async with client.stream(method, f'{self.url}{path}', content=content, params=params, headers=self._headers(), timeout=timeout) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    yield chunk

    def _headers(self) -> dict[str, str] | None:
        headers = {'Content-Type': 'application/json; charset=UTF-8'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
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
