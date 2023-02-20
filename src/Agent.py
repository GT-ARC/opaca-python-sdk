from pydantic import BaseModel
from typing import List
import uuid

from model import AgentDescription
from src import Action, Message
from src.Utils import http_error


class Agent(BaseModel):

    agent_id: str = str(uuid.uuid4())
    agent_type: str = ''
    actions: dict[str, Action] = {}
    messages: list[Message] = []

    def get_action(self, name: str):
        """
        todo: refactor action into dict?
        """
        if name in self.actions:
            return self.actions[name]
        return None


    def add_action(self, action: Action):
        self.actions[action.name] = action

    def invoke_action(self, name: str, parameters: dict):
        action = self.get_action(name)
        if action is not None:
            return action.invoke(parameters)
        raise http_error(400, f'Unknown action: {name}.')

    def receive_message(self, message: Message) -> str:
        """
        todo: do something with message
        """
        self.messages.append(message)
        return f"Successfully received message: {message}."

    def make_description(self) -> AgentDescription:
        return AgentDescription(
            agentId=self.agent_id,
            agentType=self.agent_type,
            actions=[action.make_description() for action in self.actions.values()]
        )
