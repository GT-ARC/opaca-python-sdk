from typing import Dict, List
import uuid

from src import Container
from Models import AgentDescription, ActionDescription, Message
from src.Utils import http_error


class AbstractAgent:

    def __init__(self, agent_id: str = '', agent_type: str = '', container: Container = None):
        self.agent_id: str = agent_id if agent_id else str(uuid.uuid4())
        self.agent_type: str = agent_type
        self.container: Container = container
        self.actions: Dict[str, Dict] = {}
        self.streams: Dict[str, Dict] = {}
        self.messages: List[Message] = []

    def get_action(self, name: str):
        """
        Get data about the action with the specified name.
        """
        if name in self.actions:
            return self.actions[name]
        return None

    def knows_action(self, name: str) -> bool:
        """
        Check if the agent knows the action with the given name.
        """
        return self.get_action(name) is not None

    def add_action(self, name: str, callback, parameters: Dict[str, str], result: str):
        """
        Add an action to the publicly visible list of actions this agent can perform.
        """
        self.actions[name] = {
            'name': name,
            'callback': callback,
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
            return action['callback'](**parameters)
        except TypeError:
            raise http_error(400, f'Invalid action parameters. Provided: {parameters}, Needed: {action["parameters"]}')

    def receive_message(self, message: Message):
        """
        Override in subclasses to do something with the message.
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
            actions=[self.make_action_description(action_name) for action_name in self.actions]
        )

    def make_action_description(self, action_name: str):
        action = self.actions[action_name]
        return ActionDescription(
            name=action['name'],
            parameters=action['parameters'],
            result=action['result']
        )
