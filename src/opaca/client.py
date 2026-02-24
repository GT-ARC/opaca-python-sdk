import httpx
import asyncio
from typing import Any

from .models import ContainerDescription, PlatformInfo, PostContainer, Login, AgentDescription, ConnectionRequest


class AsyncOpacaClient:

    def __init__(self, url: str):
        self.url: str = url
        self.token: str | None = None
        self.container_tokens: dict[str, str] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def __aenter__(self) -> 'AsyncOpacaClient':
        await self._lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._lock.release()

    ### AUTHENTICATION ###

    async def platform_login(self, username: str, password: str) -> None:
        body = Login(username=username, password=password).model_dump(mode='json')
        response = await self._post('/login', body=body)
        self.token = response.text

    async def renew_token(self) -> None:
        response = await self._get('/token')
        self.token = response.text

    async def container_login(self, container_id: str, username: str, password: str) -> str:
        body = Login(username=username, password=password).model_dump(mode='json')
        response = await self._post(f'/containers/login/{container_id}', body=body)
        self.container_tokens[container_id] = str(response.text)
        return self.container_tokens[container_id]

    async def container_logout(self, container_id: str) -> bool:
        if container_id not in self.container_tokens: return False
        response = await self._post(f'/containers/logout/{container_id}')
        del self.container_tokens[container_id]
        return response.json()

    ### CONTAINERS ###

    async def get_containers(self) -> list[ContainerDescription]:
        response = await self._get('/containers')
        return [ContainerDescription.model_validate(container)
                for container in response.json()]

    async def post_container(self, post_container: PostContainer) -> str:
        body = post_container.model_dump(mode='json')
        response = await self._post('/containers', body=body)
        return response.text

    async def put_container(self, post_container: PostContainer) -> str:
        body = post_container.model_dump(mode='json')
        response = await self._put('/containers', body=body)
        return response.text

    async def delete_container(self, container_id: str) -> bool:
        response = await self._delete(f'/containers/{container_id}')
        return response.json()

    async def post_container_notify(self, container_id: str) -> bool:
        response = await self._post(f'/containers/notify', body=container_id)
        return response.json()

    ### AGENTS ###

    async def get_agents(self) -> list[AgentDescription]:
        response = await self._get('/agents')
        return [AgentDescription.model_validate(agent) for agent in response.json()]

    async def get_agent(self, agent_id: str) -> AgentDescription:
        response = await self._get(f'/agents/{agent_id}')
        return AgentDescription.model_validate(response.json())

    async def invoke(
            self,
            action: str,
            agent_id: str | None = None,
            container_id: str | None = None,
            args: dict[str, Any] | None = None
    ) -> Any | None:
        path = (f'/invoke/{action}'
            + (f'/{agent_id}' if agent_id else '')
            + (f'?containerId={container_id}' if container_id else ''))
        if args is None:
            args = {}
        response = await self._post(path, body=args)
        return response.json()

    ### CONNECTIONS ###

    async def get_connections(self) -> list[str]:
        response = await self._get(f'{self.url}/connections')
        return response.json()

    async def post_connection(self, connection: str, connect_back: bool = False) -> bool:
        body = {'url': connection, 'connectBack': connect_back, 'token': None}
        response = await self._post('/connections', body=body)
        return response.json()

    async def delete_connection(self, connection: str, connect_back: bool = False) -> bool:
        body = ConnectionRequest(url=connection, connectBack=connect_back).model_dump(mode='json')
        response = await self._request('DELETE', f'/connections', body=body)
        return response.json()

    async def post_connection_notify(self, connection: str) -> bool:
        response = await self._post('/connections/notify', body=connection)
        return response.json()

    ### INFO ###

    async def get_info(self) -> PlatformInfo:
        response = await self._get('/info')
        return PlatformInfo.model_validate(response.json())

    async def get_config(self) -> dict[str, Any]:
        response = await self._get('/config')
        return response.json()

    ### PRIVATE HELPER METHODS ###

    async def _get(self, path: str, timeout=10) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{self.url}{path}', headers=self._headers(), timeout=timeout)
            response.raise_for_status()
            return response

    async def _post(self, path: str, body: Any | None = None, timeout=10) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            response = await client.post(f'{self.url}{path}', json=body, headers=self._headers(), timeout=timeout)
            response.raise_for_status()
            return response

    async def _put(self, path: str, body: Any | None = None, timeout=10) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            response = await client.put(f'{self.url}{path}', json=body, headers=self._headers(), timeout=timeout)
            response.raise_for_status()
            return response

    async def _delete(self, path: str, timeout=10) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f'{self.url}{path}', headers=self._headers(), timeout=timeout)
            response.raise_for_status()
            return response

    async def _request(self, method: str, path: str, body: Any | None = None, timeout=10) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, f'{self.url}{path}', json=body, headers=self._headers(), timeout=timeout)
            response.raise_for_status()
            return response

    def _headers(self) -> dict[str, str] | None:
        headers = {'Content-Type': 'application/json; charset=UTF-8'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
