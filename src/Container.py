from datetime import datetime, timezone
from typing import Dict, List, Optional

from src import AbstractAgent
from Models import ContainerDescription, AgentDescription, Message, ImageDescription, StreamDescription
from src.Utils import http_error


class Container:

    def __init__(self, container_id: str, platform_url: str, image: ImageDescription):
        self.container_id: str = container_id
        self.platform_url: str = platform_url
        self.image: ImageDescription = image
        self.agents: Dict[str, AbstractAgent] = {}
        self.started_at: datetime = datetime.utcnow()
        self.channels: Dict[str, List[AbstractAgent]] = {}

    def get_agent(self, agent_id: str) -> AbstractAgent:
        """
        Get the agent with the specified agent_id.
        """
        if self.has_agent(agent_id):
            return self.agents[agent_id]
        raise http_error(400, f'Unknown agentId: {agent_id}.')

    def add_agent(self, agent: AbstractAgent):
        """
        Add the agent to this container.
        """
        if not self.has_agent(agent.agent_id):
            self.agents[agent.agent_id] = agent
            agent.container = self

    def remove_agent(self, agent_id: str):
        """
        Remove the agent from the container.
        """
        if self.has_agent(agent_id):
            del self.agents[agent_id]

    def has_agent(self, agent_id) -> bool:
        return agent_id in self.agents

    def invoke_action(self, name: str, parameters: Dict[str, str]) -> str:
        """
        Invoke action on any agent that knows the action.
        """
        for agent in self.agents.values():
            if agent.knows_action(name):
                return agent.invoke_action(name, parameters)
        raise http_error(400, f'Unknown action: {name}.')

    def invoke_agent_action(self, name: str, agent_id: str, parameters: Dict[str, str]):
        """
        Invoke action on the specified agent.
        """
        if self.has_agent(agent_id):
            return self.get_agent(agent_id).invoke_action(name, parameters)
        raise http_error(400, f'Unknown agent: {agent_id}.')

    def invoke_stream(self, name: str, mode: StreamDescription.Mode):
        """
        GET a stream from or POST a stream to any agent that knows the stream.
        """
        for agent in self.agents.values():
            if agent.knows_stream(name):
                return agent.invoke_stream(name, mode)
        raise http_error(400, f'Unknown stream: {name}.')

    def invoke_agent_stream(self, name: str, mode: StreamDescription.Mode, agent_id: str = '') -> bytes:
        """
        GET a stream from or POST a stream to the specified agent.
        """
        if self.has_agent(agent_id):
            return self.get_agent(agent_id).invoke_stream(name, mode)
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

    def get_description(self) -> ContainerDescription:
        return ContainerDescription(
            containerId=self.container_id,
            image=self.image,
            agents=self.get_agent_descriptions(),
            runningSince=self.get_running_since(),
            connectivity=None
        )

    def get_agent_descriptions(self) -> List[AgentDescription]:
        return [agent.make_description() for agent in self.agents.values()]

    def get_running_since(self):
        return self.started_at.isoformat(timespec="milliseconds") + "Z"
