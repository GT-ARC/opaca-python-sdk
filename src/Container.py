from datetime import datetime
from typing import Dict, List, Optional

from src import AbstractAgent
from Models import ContainerDescription, AgentDescription, Message, ImageDescription
from src.Utils import http_error


class Container:

    def __init__(self, container_id: str, platform_url: str):
        self.container_id: str = container_id
        self.platform_url: str = platform_url
        self.agents: Dict[str, AbstractAgent] = {}
        self.started_at: datetime = datetime.now()
        self.actions: Dict[str, List[AbstractAgent]] = {}
        self.channels: Dict[str, List[AbstractAgent]] = {}
        self.image: Optional[ImageDescription] = None

    def set_image(self, **image_params: dict):
        """
        Set this container's image to a new image with the specified parameters.
        """
        self.image = ImageDescription(**image_params)

    def get_agent(self, agent_id: str) -> AbstractAgent:
        """
        Get the agent with the specified agent_id.
        """
        if agent_id in self.agents:
            return self.agents[agent_id]
        raise http_error(400, f'Unknown agentId: {agent_id}.')

    def add_agent(self, agent: AbstractAgent):
        """
        Add the agent to this container.
        """
        if agent.agent_id in self.agents:
            return
        self.agents[agent.agent_id] = agent
        agent.container = self
        self.add_agent_actions(agent)

    def remove_agent(self, agent_id: str):
        """
        Remove the agent from the container.
        """
        if agent_id not in self.agents:
            return
        agent = self.agents[agent_id]
        self.remove_agent_actions(agent)
        del self.agents[agent_id]

    def add_agent_actions(self, agent: AbstractAgent):
        """
        Add an agent's actions to this container's actions dict for quick access.
        """
        for action in agent.actions.values():
            if action['name'] not in self.actions:
                self.actions[action['name']] = []
            if agent not in self.actions[action['name']]:
                self.actions[action['name']].append(agent)

    def remove_agent_actions(self, agent: AbstractAgent):
        """
        Remove agent's actions from actions dict.
        """
        for action in agent.actions.values():
            if action['name'] not in self.actions:
                continue
            self.actions[action['name']].remove(agent)

    def invoke_action(self, name: str, parameters: Dict[str, str]) -> str:
        """
        Invoke action on any agent that knows the action.
        """
        for agent in self.agents.values():
            action = agent.get_action(name)
            if action is not None:
                return agent.invoke_action(name, parameters)
        raise http_error(400, f'Unknown action: {name}.')

    def invoke_agent_action(self, name: str, agent_id: str, parameters: Dict[str, str]):
        """
        Invoke action on the specified agent.
        """
        agent = self.get_agent(agent_id)
        if agent is not None:
            return agent.invoke_action(name, parameters)
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

    def make_description(self) -> ContainerDescription:
        return ContainerDescription(
            containerId=self.container_id,
            image=self.image,
            agents=self.get_agent_descriptions(),
            runningSince=self.get_running_since()
        )

    def get_agent_descriptions(self) -> List[AgentDescription]:
        return [agent.make_description() for agent in self.agents.values()]

    def get_running_since(self):
        return [
            self.started_at.year,
            self.started_at.month,
            self.started_at.day,
            self.started_at.hour,
            self.started_at.minute,
            self.started_at.second,
            self.started_at.microsecond
        ]
