from time import sleep

from opaca_py import action, stream
from opaca_py.abstract_agent import AbstractAgent
from opaca_py.models import Message, StreamDescription


class SampleAgent(AbstractAgent):
    """
    Sample Agent class that inherits from AbstractAgent.
    Prints some information when receiving messages or executing actions.
    """

    def __init__(self, **kwargs):
        super(SampleAgent, self).__init__(**kwargs)

    @action
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

    @action
    def concatenate(self, array: list[str], separator: str = ', ') -> str:
        """
        Concatenates the given array to a string and returns the result.
        """
        print(f'{self.agent_id} executing concatenate with params: {array}, {separator}')
        return separator.join(array)

    @stream(mode=StreamDescription.Mode.GET)
    async def sample_stream(self):
        """
        Returns a sample stream value.
        """
        yield b'sampleStream data'

    def receive_message(self, message: Message):
        super().receive_message(message)
        print(f'{self.agent_id} received message: {message}')
