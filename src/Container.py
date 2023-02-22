from pydantic import BaseModel
from datetime import datetime

from src import AbstractAgent
from Models import ContainerDescription, AgentDescription, Message, ImageDescription
from src.Utils import http_error


class Container(BaseModel):

    container_id: str
    image: ImageDescription = None
    agents: dict[str, AbstractAgent] = {}
    running_since: datetime = datetime.now()
    actions: dict[str, list[AbstractAgent]] = {}

    def get_agent(self, agent_id: str) -> AbstractAgent:
        """
        :param agent_id:
        :return:
        """
        if agent_id in self.agents:
            return self.agents[agent_id]
        raise http_error(400, f'Unknown agentId: {agent_id}.')

    def add_agent(self, agent: AbstractAgent):
        """
        adds the agent to this container, and adds its actions to this container's
        actions dict for quick access
        """
        self.agents[agent.agent_id] = agent
        agent.container = self
        for action in agent.actions.values():
            if action['name'] not in self.actions:
                self.actions[action['name']] = []
            if agent not in self.actions[action['name']]:
                self.actions[action['name']].append(agent)

    def set_image(self, **image_params: dict):
        self.image = ImageDescription(**image_params)

    def remove_agent(self, agent_id: str):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            del self.agents[agent_id]
            for action in agent.actions.values():
                self.actions[action['name']].remove(agent)

    def invoke_action(self, name: str, parameters: dict) -> str:
        """
        :param name: name of the action
        :param parameters: dict with values for the action's parameters
        :return: result of the action
        """
        for agent in self.agents.values():
            action = agent.get_action(name)
            if action is not None:
                return agent.invoke_action(name, parameters)
        raise http_error(400, f'Unknown action: {name}.')

    def invoke_action_on_agent(self, name: str, agent_id: str, parameters: dict[str, str]):
        """
        :param name:
        :param agent_id:
        :param parameters:
        :return:
        """
        agent = self.get_agent(agent_id)
        if agent is not None:
            return agent.invoke_action(name, parameters)
        raise http_error(400, f'Unknown agent: {agent_id}.')

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
