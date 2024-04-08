from typing import Dict, List
import uuid

from src import Container
from Models import AgentDescription, ActionDescription, Message, StreamDescription, Parameter
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
        Get data for the action with the specified name.
        """
        if self.knows_action(name):
            return self.actions[name]
        return None

    def knows_action(self, name: str) -> bool:
        """
        Check if the agent knows the action with the given name.
        """
        return name in self.actions

    def add_action(self, name: str, parameters: Dict[str, Parameter], result: Parameter, callback):
        """
        Add an action to the publicly visible list of actions this agent can perform.
        """
        if not self.knows_action(name):
            self.actions[name] = {
                'name': name,
                'parameters': parameters,
                'result': result,
                'callback': callback
            }

    def remove_action(self, name: str):
        """
        Removes an action from this agent's action list.
        """
        if self.knows_action(name):
            del self.actions[name]

    def invoke_action(self, name: str, parameters: Dict):
        """
        Invoke action on this agent.
        """
        if not self.knows_action(name):
            raise http_error(400, f'Unknown action: {name}.')
        try:
            return self.get_action(name)['callback'](**parameters)
        except TypeError:
            raise http_error(400, f'Invalid action parameters. '
                                  f'Provided: {parameters}, Needed: {self.get_action(name)["parameters"]}')

    def get_stream(self, name: str):
        """
        Get data for the stream with the specified name.
        """
        if self.knows_stream(name):
            return self.streams[name]
        return None

    def knows_stream(self, name: str) -> bool:
        """
        Check if the agent knows the stream with the given name.
        """
        return name in self.streams

    def add_stream(self, name: str, mode: StreamDescription.Mode, callback):
        """
        Add a stream to this agent's action publicly visible list of streams.
        """
        if not self.knows_stream(name):
            self.streams[name] = {
                'name': name,
                'mode': mode,
                'callback': callback
            }

    def invoke_stream(self, name: str, mode: StreamDescription.Mode):
        """
        GET a stream response from this agent or POST a stream to it.
        """
        if not self.knows_stream(name):
            raise http_error(400, f'Unknown stream: {name}.')
        if mode == StreamDescription.Mode.GET:
            return self.get_stream(name)['callback']()
        elif mode == StreamDescription.Mode.POST:
            raise http_error(500, f'Functionality for POSTing streams not yet implemented.')
        else:
            raise http_error(400, f'Unknown mode: {mode}')

    def remove_stream(self, name: str):
        """
        Removes a stream from this agent's stream list.
        """
        if not self.knows_stream(name):
            del self.streams[name]

    def receive_message(self, message: Message):
        """
        Override in subclasses to do something with the message.
        """
        self.messages.append(message)

    def subscribe_channel(self, channel: str):
        """
        Subscribe to a broadcasting channel.
        """
        if self.container is not None:
            self.container.subscribe_channel(channel, self)

    def unsubscribe_channel(self, channel: str):
        """
        Subscribe to a broadcasting channel.
        """
        if self.container is not None:
            self.container.unsubscribe_channel(channel, self)

    def make_description(self) -> AgentDescription:
        return AgentDescription(
            agentId=self.agent_id,
            agentType=self.agent_type,
            actions=[self.make_action_description(action_name) for action_name in self.actions],
            streams=[self.make_stream_description(stream_name) for stream_name in self.streams]
        )


    def make_action_description(self, action_name: str):
        action = self.get_action(action_name)
        return ActionDescription(
            name=action['name'],
            parameters=action['parameters'],
            result=action['result']
        )

    def make_stream_description(self, stream_name: str):
        stream = self.get_stream(stream_name)
        return StreamDescription(
            name=stream['name'],
            mode=stream['mode']
        )
