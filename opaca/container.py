import os
import uuid
import logging
from datetime import datetime, timezone
from inspect import iscoroutinefunction
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import httpx
from starlette.responses import FileResponse

from .abstract_agent import AbstractAgent
from .recurrent_task import RecurrentTask, start_tasks
from .models import ContainerDescription, AgentDescription, Message, ImageDescription, StreamDescription, LoginMsg, \
    Login, StreamContent
from .utils import http_error, make_file_response


log = logging.getLogger(__name__)


class Container:

    def __init__(self, path_to_image_file: str) -> None:
        self.container_id: str = os.getenv('CONTAINER_ID', '')
        self.platform_url: str = os.getenv('PLATFORM_URL', '')
        self.token: str = os.getenv('TOKEN', '')
        self.owner: str = os.getenv('OWNER', '')
        self.own_url: Optional[str] = None
        self.image: ImageDescription = Container.load_image(path_to_image_file)
        self.agents: Dict[str, AbstractAgent] = {}
        self.started_at: datetime = datetime.now(timezone.utc)
        self.channels: Dict[str, List[AbstractAgent]] = {}
        self.models: Dict[str, Any] = {}
        self.recurrent_tasks: Dict[str, RecurrentTask] = {}

        self._exposed_files: Dict[str, Path] = {}

    @staticmethod
    def load_image(json_file: str) -> ImageDescription:
        """
        Load a container's image description from a JSON file.
        """
        try:
            with open(json_file, encoding='utf-8') as f:
                return ImageDescription.model_validate(json.load(f))
        except TypeError:
            raise http_error(500, 'Failed to load image description.')

    def get_agent(self, agent_id: str) -> AbstractAgent:
        """
        Get the agent with the specified agent_id.
        """
        if self.has_agent(agent_id):
            return self.agents[agent_id]
        raise http_error(400, f'Unknown agentId: {agent_id}.')

    def add_agent(self, agent: AbstractAgent) -> None:
        """
        Add the agent to this container.
        """
        if not self.has_agent(agent.agent_id):
            self.agents[agent.agent_id] = agent
            agent.container = self

    def remove_agent(self, agent_id: str) -> None:
        """
        Remove the agent from the container.
        """
        if self.has_agent(agent_id):
            del self.agents[agent_id]

    def has_agent(self, agent_id) -> bool:
        return agent_id in self.agents

    async def invoke_action(
            self,
            name: str,
            parameters: Dict[str, Any],
            login_token: str | None = None
    ) -> None:
        """
        Invoke action on any agent that knows the action.
        """
        for agent in self.agents.values():
            if agent.knows_action(name):
                return await agent.invoke_action(name, parameters, login_token)
        raise http_error(400, f'Unknown action: {name}.')

    async def invoke_agent_action(
            self,
            name: str,
            agent_id: str,
            parameters: Dict[str, Any],
            login_token: str | None = None
    ) -> Any:
        """
        Invoke action on the specified agent.
        """
        if self.has_agent(agent_id):
            return await self.get_agent(agent_id).invoke_action(name, parameters, login_token)
        raise http_error(400, f'Unknown agent: {agent_id}.')

    def invoke_stream(
            self,
            name: str,
            mode: StreamDescription.Mode,
            login_token: str | None = None
    ) -> StreamContent | None:
        """
        GET a stream from or POST a stream to any agent that knows the stream.
        """
        for agent in self.agents.values():
            if agent.knows_stream(name):
                return agent.invoke_stream(name, mode, login_token)
        raise http_error(400, f'Unknown stream: {name}.')

    def invoke_agent_stream(
            self,
            name: str,
            mode: StreamDescription.Mode,
            agent_id: str = '',
            login_token: str | None = None
    ) -> StreamContent | None:
        """
        GET a stream from or POST a stream to the specified agent.
        """
        if self.has_agent(agent_id):
            return self.get_agent(agent_id).invoke_stream(name, mode, login_token)
        raise http_error(400, f'Unknown agent: {agent_id}.')

    def send_message(self, agent_id: str, message: Message) -> None:
        """
        Send a message to the specified agent.
        """
        agent = self.get_agent(agent_id)
        if agent is not None:
            agent.receive_message(message)

    def subscribe_channel(self, channel: str, agent: AbstractAgent) -> None:
        """
        Subscribe an agent to the specified channel.
        """
        if channel not in self.channels:
            self.channels[channel] = []
        if agent not in self.channels[channel]:
            self.channels[channel].append(agent)

    def unsubscribe_channel(self, channel: str, agent: AbstractAgent) -> None:
        """
        Unsubscribe an agent from the specified channel.
        """
        if channel not in self.channels:
            return
        if agent not in self.channels[channel]:
            return
        self.channels[channel].remove(agent)

    def broadcast(self, channel: str, message: Message) -> None:
        """
        Broadcast a message to all agents subscribing to the specified channel.
        """
        if channel not in self.channels:
            return
        for agent in self.channels[channel]:
            agent.receive_message(message)

    async def handle_login(self, login: Login) -> str:
        token = str(uuid.uuid4())
        for agent in self.agents.values():
            msg = LoginMsg(token=token, login=login)
            if iscoroutinefunction(agent.handle_login):
                await agent.handle_login(msg)
            else:
                agent.handle_login(msg)
        return token

    async def handle_logout(self, login_token: str | None = None) -> bool:
        if not login_token:
            return False
        for agent in self.agents.values():
            if iscoroutinefunction(agent.handle_logout):
                await agent.handle_logout(login_token)
            else:
                agent.handle_logout(login_token)
        return True

    def get_description(self) -> ContainerDescription:
        return ContainerDescription(
            containerId=self.container_id,
            image=self.image,
            arguments=self.get_arguments(False),
            agents=self.get_agent_descriptions(),
            owner=self.owner,
            runningSince=self.get_running_since(),
            connectivity=None
        )

    def get_agent_descriptions(self) -> List[AgentDescription]:
        return [agent.make_description() for agent in self.agents.values()]

    def get_running_since(self) -> str:
        return self.started_at.isoformat(timespec="milliseconds")

    def get_arguments(self, include_confidential: bool = True) -> Dict[str, Any]:
        return { param.name: os.getenv(param.name, param.defaultValue)
                 for param in self.image.parameters
                 if include_confidential or not param.confidential }

    def find_own_url(self):
        """
        Find the container's own base url, including the API port.

        Should replace this with SyncOpacaClient call once that exists.
        """
        if not self.platform_url:
            return f'http://localhost:{self.image.apiPort}'

        if self.own_url is None:
            try:
                containers = httpx.get(f"{self.platform_url}/containers").json()
                connectivity = next(c["connectivity"] for c in containers if c["containerId"] == self.container_id)
                self.own_url = f'{connectivity["publicUrl"]}:{connectivity["apiPortMapping"]}'
            except httpx.RequestError as e:
                log.error('Failed to request own URL from the OPACA runtime platform. '
                          'Make sure that the container is known by the platform.')
                raise e

        return self.own_url

    def expose_file(self, path: str | Path) -> str:
        """Helper function to publicly expose a file
        via the '/files/{file_id}' route."""
        file_id = str(uuid.uuid4())
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f'File not found: {file_path}')
        self._exposed_files[file_id] = file_path
        return file_id

    def get_file_url(self, file_id: str) -> str:
        """Helper function to get an exposed file's full URL."""
        own_url = self.find_own_url()
        if not own_url:
            raise http_error(400,f'Could not find own URL.')
        return f'{own_url}/files/{file_id}'

    def serve_exposed_file(self, file_id: str) -> FileResponse:
        error_msg = 'File not found.'
        if file_id not in self._exposed_files:
            raise http_error(404, error_msg)
        file_path = self._exposed_files[file_id]
        if not file_path.is_file():
            self._exposed_files.pop(file_id)
            raise http_error(404, error_msg)
        return make_file_response(self._exposed_files[file_id])

    def add_recurrent_task(self, task: RecurrentTask) -> None:
        self.recurrent_tasks[task.task_id] = task

    def cancel_recurrent_task(self, task_id: str) -> None:
        self.recurrent_tasks[task_id].cancel()

    def start_recurrent_tasks(self) -> None:
        start_tasks(self.recurrent_tasks)

    def cancel_recurrent_tasks(self) -> None:
        for task_id in self.recurrent_tasks:
            self.cancel_recurrent_task(task_id)