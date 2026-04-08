import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import json

from .abstract_agent import AbstractAgent
from .models import ContainerDescription, AgentDescription, Message, ImageDescription, StreamDescription, LoginMsg, \
    Login, StreamContent
from .utils import http_error


class Container:

    def __init__(self, path_to_image_file: str) -> None:
        self.container_id = os.getenv('CONTAINER_ID', '')
        self.platform_url = os.getenv('PLATFORM_URL', '')
        self.token = os.getenv('TOKEN', '')
        self.owner = os.getenv('OWNER', '')

        self.image: ImageDescription = Container.load_image(path_to_image_file)
        self.agents: Dict[str, AbstractAgent] = {}
        self.started_at: datetime = datetime.now(timezone.utc)
        self.channels: Dict[str, List[AbstractAgent]] = {}

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
            login_token: str = None
    ) -> None:
        """
        Invoke action on any agent that knows the action.
        """
        for agent in self.agents.values():
            if agent.knows_action(name):
                return await agent.invoke_action(name, parameters, login_token)
        raise http_error(400, f'Unknown action: {name}.')

    async def invoke_agent_action(self, name: str, agent_id: str, parameters: Dict[str, Any], login_token: str = None):
        """
        Invoke action on the specified agent.
        """
        if self.has_agent(agent_id):
            return await self.get_agent(agent_id).invoke_action(name, parameters, login_token)
        raise http_error(400, f'Unknown agent: {agent_id}.')

    def invoke_stream(self, name: str, mode: StreamDescription.Mode, login_token: str = None):
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
            login_token: str = None
    ) -> Optional[StreamContent]:
        """
        GET a stream from or POST a stream to the specified agent.
        """
        if self.has_agent(agent_id):
            return self.get_agent(agent_id).invoke_stream(name, mode, login_token)
        raise http_error(400, f'Unknown agent: {agent_id}.')

    def send_message(self, agent_id: str, message: Message):
        """
        Send a message to the specified agent.
        """
        agent = self.get_agent(agent_id)
        if agent is not None:
            agent.receive_message(message)

    def subscribe_channel(self, channel: str, agent: AbstractAgent):
        """
        Subscribe an agent to the specified channel.
        """
        if channel not in self.channels:
            self.channels[channel] = []
        if agent not in self.channels[channel]:
            self.channels[channel].append(agent)

    def unsubscribe_channel(self, channel: str, agent: AbstractAgent):
        """
        Unsubscribe an agent from the specified channel.
        """
        if channel not in self.channels:
            return
        if agent not in self.channels[channel]:
            return
        self.channels[channel].remove(agent)

    def broadcast(self, channel: str, message: Message):
        """
        Broadcast a message to all agents subscribing to the specified channel.
        """
        if channel not in self.channels:
            return
        for agent in self.channels[channel]:
            agent.receive_message(message)

    def handle_login(self, login: Login) -> str:
        token = str(uuid.uuid4())
        for agent in self.agents.values():
            agent.handle_login(LoginMsg(token=token, login=login))
        return token

    def handle_logout(self, login_token: str = None) -> bool:
        if not login_token:
            return False
        for agent in self.agents.values():
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
