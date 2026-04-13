from typing import Dict, List, Any, Optional, Callable, TYPE_CHECKING
from inspect import getdoc, iscoroutinefunction
from pydantic import ValidationError, BaseModel
import uuid
import logging

from .models import AgentDescription, ActionDescription, Message, StreamDescription, Parameter, LoginMsg, StreamContent
from .utils import http_error
from .decorators import register_actions, register_streams

if TYPE_CHECKING:
    from .container import Container


log = logging.getLogger(__name__)


class AbstractAgent:

    def __init__(
            self,
            container: 'Container',
            agent_id: str = '',
            agent_type: str = '',
            description: Optional[str] = None
    ) -> None:
        self.container: 'Container' = container
        self.agent_id: str = agent_id if agent_id else str(uuid.uuid4())
        self.agent_type: str = agent_type or self.__class__.__name__
        self.description: Optional[str] = description or getdoc(self.__class__)
        self.actions: Dict[str, ActionDescription] = {}
        self.streams: Dict[str, StreamDescription] = {}
        self.messages: List[Message] = []

        self.container.add_agent(self)
        register_actions(self)
        register_streams(self)

    def get_action(self, name: str) -> ActionDescription:
        """
        Get data for the action with the specified name.
        """
        return self.actions[name]

    def knows_action(self, name: str) -> bool:
        """
        Check if the agent knows the action with the given name.
        """
        return name in self.actions

    def add_action(
            self,
            name: str,
            description: Optional[str],
            parameters: Dict[str, Parameter],
            result: Parameter,
            callback: Callable
    ) -> None:
        """
        Add an action to the publicly visible list of actions this agent can perform.
        """
        if self.knows_action(name): return
        self.actions[name] = ActionDescription(
            name=name,
            description=description,
            parameters=parameters,
            result=result,
            callback=callback,
        )

    def remove_action(self, name: str):
        """
        Removes an action from this agent's action list.
        """
        if self.knows_action(name):
            del self.actions[name]

    async def invoke_action(
            self,
            name: str,
            parameters: Dict[str, Any],
            login_token: str = None
    ) -> Optional[Any]:
        """
        Invoke action on this agent.
        """
        if not self.knows_action(name):
            raise http_error(400, f'Unknown action: {name}.')

        try:
            action = self.get_action(name)
            callback = action.callback

            parameters = self.parse_custom_types(name, parameters)

            if getattr(callback, '_auth', False):
                if not login_token:
                    raise http_error(401, 'Missing credentials')
                parameters['login_token'] = login_token

            if iscoroutinefunction(callback):
                return await callback(**parameters)
            else:
                return callback(**parameters)

        except TypeError:
            if "login_token" in parameters.keys():
                parameters.pop("login_token")
            msg = f'Invalid action parameters. Provided: {parameters}, Required: {self.get_action(name).parameters}'
            raise http_error(400, msg)

    def get_stream(self, name: str) -> StreamDescription:
        """
        Get data for the stream with the specified name.
        """
        return self.streams[name]

    def knows_stream(self, name: str) -> bool:
        """
        Check if the agent knows the stream with the given name.
        """
        return name in self.streams

    def add_stream(
            self,
            name: str,
            description: Optional[str],
            mode: StreamDescription.Mode,
            callback: Callable
    ) -> None:
        """
        Add a stream to this agent's action publicly visible list of streams.
        """
        if not self.knows_stream(name):
            self.streams[name] = StreamDescription(
                name=name,
                description=description,
                mode=mode,
                callback=callback,
            )

    def invoke_stream(
            self,
            name: str,
            mode: StreamDescription.Mode,
            login_token: str = None
    ) -> StreamContent | None:
        """
        GET a stream response from this agent or POST a stream to it.
        """
        if not self.knows_stream(name):
            raise http_error(400, f'Unknown stream: {name}.')

        if mode == StreamDescription.Mode.GET:
            if getattr(self.get_stream(name).callback, '_auth', False):
                return self.get_stream(name).callback(login_token)
            return self.get_stream(name).callback()
        elif mode == StreamDescription.Mode.POST:
            raise http_error(500, f'Functionality for POSTing streams not yet implemented.')
        else:
            raise http_error(400, f'Unknown mode: {mode}')

    def remove_stream(self, name: str) -> None:
        """
        Removes a stream from this agent's stream list.
        """
        if self.knows_stream(name):
            del self.streams[name]

    def receive_message(self, message: Message) -> None:
        """
        Override in subclasses to do something with the message.
        """
        self.messages.append(message)

    def subscribe_channel(self, channel: str) -> None:
        """
        Subscribe to a broadcasting channel.
        """
        self.container.subscribe_channel(channel, self)

    def unsubscribe_channel(self, channel: str) -> None:
        """
        Unsubscribe from a broadcasting channel.
        """
        self.container.unsubscribe_channel(channel, self)

    async def handle_login(self, login_msg: LoginMsg) -> None:
        """
        Implement this method in your agent to handle login requests for any external services.

        The loginMsg contains the 'username' and 'password' provided by the user, as well as a random
        UUID token, which can be used to associate retrieved login details with this specific user.
        """
        pass

    async def handle_logout(self, login_token: str) -> None:
        """
        Implement this method in your agent to handle logout requests for any external services.
        Use the provided login_token to identify the user.
        """
        pass

    def make_description(self) -> AgentDescription:
        return AgentDescription(
            agentId=self.agent_id,
            agentType=self.agent_type,
            description=self.description,
            actions=[action for action in self.actions.values()],
            streams=[stream for stream in self.streams.values()],
        )

    def parse_custom_types(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Parse any parameters that are defined as custom types into the corresponding model class.
        """
        def parse_value(value: Any, cls: type[BaseModel]) -> Any:
            try:
                return cls.model_validate(value)
            except ValidationError as e:
                log.error(e)
                return value

        def parse_list_value(value: Any, cls: type[BaseModel]) -> Any:
            try:
                return [cls.model_validate(item) for item in value]
            except ValidationError as e:
                log.error(e)
                return value

        def parse_param(name: str, value: Any) -> Any:
            defs = self.container.definitions
            param = self.actions[action].parameters[name]

            if param.type == 'array' and param.items is not None:
                items: Parameter.ArrayItems = param.items
                if items.type in self.container.definitions:
                    return parse_list_value(value, defs[items.type])

            elif param.type in self.container.definitions:
                return parse_value(value, defs[param.type])

            return value

        return {
            name: parse_param(name, value)
            for name, value in parameters.items()
        }