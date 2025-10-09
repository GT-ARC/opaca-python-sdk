import uuid
from time import sleep
from typing import Dict, Callable

from fastapi import HTTPException

from opaca import action, stream
from opaca.abstract_agent import AbstractAgent
from opaca.models import Message, StreamDescription, Parameter, Login, LoginMsg


class SampleAgent(AbstractAgent):
    """
    Sample Agent class that inherits from AbstractAgent.
    Prints some information when receiving messages or executing actions.
    """

    def __init__(self, **kwargs):
        super(SampleAgent, self).__init__(**kwargs)
        self.clients: Dict[str, Callable] = {}
        self.add_action(
            name='SampleAction',
            description='Returns a simple string acknowledging the action\'s execution with the given parameters.',
            parameters={'param1': Parameter(type='string'), 'param2': Parameter(type='integer')},
            result=Parameter(type='string'),
            callback=self.sample_action
        )
        self.add_stream(
            name='SampleStream',
            description='Returns a sample stream value.',
            mode=StreamDescription.Mode.GET,
            callback=self.sample_stream
        )

    # Actions

    def sample_action(self, param1: str, param2: int) -> str:
        """
        Returns a simple string acknowledging the action\'s execution with the given parameters.
        """
        return f'{self.agent_id} executed sampleAction1 with params: {param1}, {param2}'

    @action
    def add(self, x: int, y: int) -> int:
        """
        Adds the two numbers and returns the result.
        """
        print(f'{self.agent_id} executed add with params: {x}, {y}')
        return x + y

    @action
    def time_consuming_action(self, text: str, sleep_time: int = 0) -> str:
        """
        Returns the given text after waiting for the given time + 1 in seconds.
        """
        sleep_time = int(sleep_time)
        print(f'{self.agent_id} executing time_consuming action, taking approx {1 + sleep_time} seconds')
        sleep(1 + sleep_time)
        return text

    @action(name='ConcatenateArray', description='Concatenates the given array to a string and returns the result.')
    def concatenate(self, array: list[str], separator: str = ', ') -> str:
        print(f'{self.agent_id} executing concatenate with params: {array}, {separator}')
        return separator.join(array)

    # Streams

    async def sample_stream(self):
        """
        Returns a sample stream value.
        """
        yield b'sampleStream data'

    @stream(mode=StreamDescription.Mode.GET)
    async def sample_stream_deco(self):
        """
        Returns a sample stream value.
        """
        yield b'sampleStream data'

    # Container Login

    async def handle_login(self, login_msg: LoginMsg):
        """
        This method should construct a login token specific client for an external api requiring auth.
        """
        # Perform external API login
        self.clients[login_msg.token] = lambda: f'Logged in as user: {login_msg.login.username}'

    async def handle_logout(self, login_token: str):
        """
        This method should remove the callable client associated to the login token.
        """
        del self.clients[login_token]

    @action(auth=True)
    async def login_test(self, login_token: str) -> str:
        """
        After a successful login, use the constructed client to perform some action.
        It is important that actions with enabled authentication define the "login_token" parameter.
        """
        if login_token not in self.clients.keys():
            raise HTTPException(status_code=403, detail='Forbidden')
        return f'Calling authenticated client with login_token: {login_token}\n{self.clients[login_token]()}'

    @stream(mode=StreamDescription.Mode.GET, auth=True)
    async def login_test_stream(self, login_token: str):
        """
        Streams requiring authentication work very similarly to actions.
        """
        if login_token not in self.clients.keys():
            raise HTTPException(status_code=403, detail='Forbidden')
        yield b'Calling authenticated stream with login_token: ' + login_token.encode() + b'\n' + self.clients[login_token]().encode()

    def receive_message(self, message: Message):
        super().receive_message(message)
        print(f'{self.agent_id} received message: {message}')
