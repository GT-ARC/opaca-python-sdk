from time import sleep

from opaca import action, stream
from opaca.abstract_agent import AbstractAgent
from opaca.models import Message, StreamDescription, Parameter


class SampleAgent(AbstractAgent):
    """
    Sample Agent class that inherits from AbstractAgent.
    Prints some information when receiving messages or executing actions.
    """

    def __init__(self, **kwargs):
        super(SampleAgent, self).__init__(**kwargs)
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

    def receive_message(self, message: Message):
        super().receive_message(message)
        print(f'{self.agent_id} received message: {message}')
