import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, TYPE_CHECKING
from inspect import getdoc, iscoroutinefunction
from pydantic import ValidationError
import uuid
import logging

from .client import AsyncOpacaClient
from .models import AgentDescription, ActionDescription, Message, StreamDescription, Parameter, LoginMsg, StreamContent
from .recurrent_task import RecurrentTask
from .utils import http_error
from .decorators import _register_actions, _register_streams, _update_definitions, _register_recurrent

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
        self.recurrent_tasks: Dict[str, RecurrentTask] = {}
        self.container.add_agent(self)

        _register_actions(self)
        _register_streams(self)
        _update_definitions(self)
        _register_recurrent(self)

    @property
    def platform_client(self) -> AsyncOpacaClient:
        return self.container.platform_client

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

    def remove_action(self, name: str) -> None:
        """
        Removes an action from this agent's action list.
        """
        if self.knows_action(name):
            del self.actions[name]

    async def invoke_action(
            self,
            name: str,
            parameters: Dict[str, Any],
            login_token: str | None = None
    ) -> Optional[Any]:
        """
        Invoke action on this agent.
        """
        if not self.knows_action(name):
            raise http_error(400, f'Unknown action: {name}.')

        try:
            action = self.get_action(name)
            callback = action.callback
            if not callback: return None

            parameters = self._parse_custom_types(name, parameters)

            if getattr(callback, '_auth', False):
                if not login_token:
                    raise http_error(401, 'Missing credentials')
                parameters['login_token'] = login_token

            # Inject default values in case the action was defined via self.add_action(...)
            for param_name, param in action.parameters.items():
                if param.defaultValue is not None and param_name not in parameters:
                    parameters[param_name] = param.defaultValue

            if iscoroutinefunction(callback):
                return await callback(**parameters)
            else:
                return callback(**parameters)

        except Exception as e:
            raise http_error(400, f'Failed to invoke action {name!r}: {e}\n{traceback.format_exception(e)}')

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

    def remove_stream(self, name: str) -> None:
        """
        Removes a stream from this agent's stream list.
        """
        if self.knows_stream(name):
            del self.streams[name]

    def invoke_stream(
            self,
            name: str,
            mode: StreamDescription.Mode,
            login_token: str | None = None
    ) -> StreamContent | None:
        """
        GET a stream response from this agent or POST a stream to it.
        """
        if not self.knows_stream(name):
            raise http_error(400, f'Unknown stream: {name}.')

        stream = self.get_stream(name)
        callback = stream.callback
        if not callback: return None

        if mode == StreamDescription.Mode.GET:
            if getattr(callback, '_auth', False):
                return callback(login_token)
            return callback()
        elif mode == StreamDescription.Mode.POST:
            raise http_error(500, f'Functionality for POSTing streams not yet implemented.')
        else:
            raise http_error(400, f'Unknown mode: {mode}')

    def receive_message(self, message: Message) -> None:
        """
        This is called when the agent receives a message via the POST /send route.
        Implement this method in your agent to do something with the message.
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

    def make_model(self) -> AgentDescription:
        return AgentDescription(
            agentId=self.agent_id,
            agentType=self.agent_type,
            description=self.description,
            actions=[action for action in self.actions.values()],
            streams=[stream for stream in self.streams.values()],
        )

    def _parse_custom_types(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Parse any parameters that are defined as custom types into the corresponding model class.
        """
        models = self.container._base_models

        def parse_model(value: Any, param: Parameter | Parameter.ArrayItems) -> Any:
            if param.type == 'array':
                if param.items is None or not isinstance(value, list): return value
                return [parse_model(item, param.items) for item in value]

            if param.type in models:
                cls = models[param.type]
                return cls.model_validate(value)

            return value

        def parse_param(name: str, value: Any) -> Any:
            try:
                param = self.actions[action].parameters[name]
                return parse_model(value, param)
            except (KeyError, ValidationError) as e:
                log.error(e)
                return value

        return {
            name: parse_param(name, value)
            for name, value in parameters.items()
        }

    def expose_file(self, path: str | Path) -> str:
        """
        Expose a file to be publicly available
        via the '/files/{file_id}' route.

        Call `self.get_file_url(file_id)` to get the full URL where
        the file is available.

        :param path: The path to the file.
        :return: The new file_id for the file.
        """
        return self.container.expose_file(path)

    def get_file_url(self, file_id: str) -> str:
        """
        Get the full URL for an exposed file.

        This is only usable AFTER the container is online and the
        platform was able to communicate with it.
        """
        return self.container.get_file_url(file_id)

    def cancel_recurrent_task(self, task_id: str) -> None:
        """
        Cancel a recurrent task.
        """
        self.recurrent_tasks[task_id].cancel()
