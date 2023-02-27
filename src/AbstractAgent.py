from pydantic import BaseModel
from typing import Dict, List
import uuid

from Models import AgentDescription, ActionDescription, Message
from src.Utils import http_error


class AbstractAgent(BaseModel):

    container: 'Container' = None
    agent_id: str = str(uuid.uuid4())
    agent_type: str = ''
    actions: Dict[str, dict] = {}
    messages: List[Message] = []

    def get_action(self, name: str):
        """
        Get data about the action with the specified name.
        """
        if name in self.actions:
            return self.actions[name]
        return None

    def add_action(self, name: str, action, parameters: Dict[str, str], result: str):
        """
        Add an action to the publicly visible list of actions this agent can perform.
        """
        self.actions[name] = {
            'name': name,
            'action': action,
            'parameters': parameters,
            'result': result
        }

    def invoke_action(self, name: str, parameters: Dict):
        """
        Invoke action on this agent.
        """
        action = self.get_action(name)
        if action is None:
            raise http_error(400, f'Unknown action: {name}.')
        try:
            return action['action'](**parameters)
        except TypeError:
            raise http_error(400, f'Invalid action parameters. Provided: {parameters}, Needed: {action["parameters"]}')

    def receive_message(self, message: Message):
        """
        todo: do something with message
        """
        self.messages.append(message)

    def subscribe_channel(self, channel: str):
        """
        Subscribe to a broadcasting channel.
        """
        if self.container is None:
            return
        self.container.subscribe_channel(channel, self)

    def unsubscribe_channel(self, channel: str):
        """
        Subscribe to a broadcasting channel.
        """
        if self.container is None:
            return
        self.container.unsubscribe_channel(channel, self)

    def make_description(self) -> AgentDescription:
        return AgentDescription(
            agentId=self.agent_id,
            agentType=self.agent_type,
            actions=[self.make_action_description(action) for action in self.actions.values()]
        )

    def make_action_description(self, action: Dict):
        return ActionDescription(
            name=action['name'],
            parameters=action['parameters'],
            result=action['result']
        )
