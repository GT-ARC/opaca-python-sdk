from pydantic import BaseModel
from datetime import datetime
import uuid

from src import ContainerImage, Agent, Message
from src.Utils import http_error


class Container(BaseModel):

    container_id: str
    image: ContainerImage | None
    agents: list[Agent]
    running_since: datetime

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
        for agent in self.agents:
            if agent.agentId == agentId:
                return agent
        raise http_error(400, f'Unknown agentId: {agentId}.')

    def set_image(self, **image_params: dict):
        self.image = ContainerImage(**image_params)

    def add_agent(self, agent: Agent):
        self.agents.append(agent)

    def remove_agent(self, agentId: str):
        try:
            agent = self.get_agent(agentId)
            self.agents.remove(agent)
        except ValueError: pass

    def invoke_action(self, name: str, parameters: dict) -> str:
        for agent in self.agents:
            for action in agent.actions:
                if action.name == name:
                    return action.invoke(parameters)
        raise http_error(400, f'Unknown action: {name}.')

    def send_message(self, agentId: str, message: Message) -> str:
        agent = self.get_agent(agentId)
        if agent is not None:
            return agent.receive_message(message)
        raise http_error(400, f'Unknown agentId: {agentId}.')


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
