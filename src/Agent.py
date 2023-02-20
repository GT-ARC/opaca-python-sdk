from pydantic import BaseModel
from typing import List
import uuid

from src import Action, Message
from src.Utils import http_error


class Agent(BaseModel):

    agentId: str
    agentType: str
    actions: list[Action]

    def __init__(self, agentId: str = '', agentType: str = '', actions: list = None):
        super(Agent, self).__init__(
            agentId = agentId or str(uuid.uuid4()),
            agentType = agentType,
            actions = actions or []
        )

    def get_action(self, name: str):
        """
        todo: refactor action into dict?
        """
        for action in self.actions:
            if action.name == name:
                return action
        return None


    def add_action(self, action: Action):
        self.actions.append(action)

    def invoke_action(self, name: str, parameters: dict):
        action = self.get_action(name)
        if action is not None:
            action.invoke(parameters)
        raise http_error(400, f'Unknown action: {name}.')

    def receive_message(self, message: Message):
        """
        todo: do something with message
        """
        return f"Successfully received message: {message}."
