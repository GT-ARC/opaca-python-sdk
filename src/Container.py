from pydantic import BaseModel
from datetime import datetime
import uuid

from model import ContainerDescription, AgentDescription, Message, ImageDescription
from src import ContainerImage, Agent
from src.Utils import http_error


class Container(BaseModel):

    container_id: str = str(uuid.uuid4())
    image: ImageDescription = None
    agents: dict[str, Agent] = {}
    running_since: datetime = datetime.now()
    actions: dict[str, list[Agent]] = {}

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
        self.image = ImageDescription(**image_params)

    def remove_agent(self, agent_id: str):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            del self.agents[agent_id]
            for action in agent.actions.values():
                self.actions[action.name].remove(agent)

    def invoke_action(self, name: str, parameters: dict, agent_id: str = '') -> str:
        if agent_id == '':
            for agent in self.agents.values():
                action = agent.get_action(name)
                if action is not None:
                    return action.invoke(parameters)
            raise http_error(400, f'Unknown action: {name}.')
        else:
            agent = self.get_agent(agent_id)
            if agent is not None:
                return agent.invoke_action(name, parameters)
            raise http_error(400, f'Unknown action: {name}.')


    def send_message(self, agent_id: str, message: Message) -> str:
        agent = self.get_agent(agent_id)
        if agent is not None:
            return agent.receive_message(message)
        raise http_error(400, f'Unknown agentId: {agent_id}.')

    def make_description(self) -> ContainerDescription:
        return ContainerDescription(
            containerId=self.container_id,
            image=self.image,
            agents=self.get_agent_descriptions(),
            runningSince=self.get_running_since()
        )

    def get_agent_descriptions(self) -> list[AgentDescription]:
        return [agent.make_description() for agent in self.agents.values()]


    def get_running_since(self):
        return [
            self.running_since.year,
            self.running_since.month,
            self.running_since.day,
            self.running_since.hour,
            self.running_since.minute,
            self.running_since.second,
            self.running_since.microsecond
        ]

    def broadcast(self, channel: str, message: Message):
        pass
