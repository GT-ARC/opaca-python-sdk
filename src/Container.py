from pydantic import BaseModel
from datetime import datetime
import uuid

from model import ContainerDescription, AgentDescription
from src import ContainerImage, Agent, Message
from src.Utils import http_error


class Container(BaseModel):

    container_id: str
    image: ContainerImage | None
    agents: dict[str, Agent]
    running_since: datetime
    actions: dict[str, list[Agent]] = {}

    def __init__(self, container_id: str = '', image: ContainerImage = None, agents: list = None, running_since: datetime = None):
        super(Container, self).__init__(
            container_id = container_id or str(uuid.uuid4()),
            image = image,
            agents = agents or [],
            running_since = running_since or datetime.now()
        )

    def get_agent(self, agentId: str) -> Agent | None:
        """
        todo: refactor agents list into dict?
        """
        if agentId in self.agents:
            return self.agents[agentId]
        raise http_error(400, f'Unknown agentId: {agentId}.')

    def add_agent(self, agent: Agent):
        """
        adds the agent to this container, and adds its actions to this container's
        actions dict for quick access
        """
        self.agents[agent.agent_id] = agent
        for action in agent.actions.values():
            if action.name not in self.actions:
                self.actions[action.name] = []
            if agent not in self.actions[action.name]:
                self.actions[action.name].append(agent)

    def set_image(self, **image_params: dict):
        self.image = ContainerImage(**image_params)

    def remove_agent(self, agent_id: str):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            del self.agents[agent_id]
            for action in agent.actions.values():
                self.actions[action.name].remove(agent)

    def invoke_action(self, name: str, parameters: dict) -> str:
        for agent in self.agents.values():
            action = agent.get_action(name)
            if action is not None:
                return action.invoke(parameters)
        raise http_error(400, f'Unknown action: {name}.')

    def send_message(self, agent_id: str, message: Message) -> str:
        agent = self.get_agent(agent_id)
        if agent is not None:
            return agent.receive_message(message)
        raise http_error(400, f'Unknown agentId: {agent_id}.')

    def make_description(self) -> ContainerDescription:
        return ContainerDescription(
            containerId=self.container_id,
            agents=self.get_agent_descriptions(),
            runningSince=self.running_since
        )

    def get_agent_descriptions(self) -> list[AgentDescription]:
        return [agent.make_description() for agent in self.agents.values()]

