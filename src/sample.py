from time import sleep

from opaca_py.abstract_agent import AbstractAgent
from opaca_py.models import Message, StreamDescription, Parameter


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
        self.add_action(
            name='Add',
            description='Adds the two numbers and returns the result.',
            parameters={'x': Parameter(type='integer'), 'y': Parameter(type='integer')},
            result=Parameter(type='integer'),
            callback=self.add
        )
        self.add_action(
            name='TimeConsumingAction',
            description='Returns the given text after waiting for the given time + 1 in seconds.',
            parameters={'text': Parameter(type='string'), 'sleep_time': Parameter(type='integer')},
            result=Parameter(type='string'),
            callback=self.time_consuming_action
        )
        self.add_action(
            name='Concatenate',
            description='Concatenates the given array to a string and returns the result.',
            parameters={'array': Parameter.list_of('string'), 'separator': Parameter(type='string', required=False)},
            result=Parameter(type='string'),
            callback=self.concatenate
        )
        self.add_stream(
            name='SampleStream',
            description='Returns a sample stream value.',
            mode=StreamDescription.Mode.GET,
            callback=self.sample_stream
        )

    def sample_action(self, param1: str, param2: int) -> str:
        return f'{self.agent_id} executed sampleAction1 with params: {param1}, {param2}'

    def add(self, x: int, y: int) -> int:
        print(f'{self.agent_id} executed add with params: {x}, {y}')
        return x + y

    def time_consuming_action(self, text: str, sleep_time: int = 0) -> str:
        sleep_time = int(sleep_time)
        print(f'{self.agent_id} executing time_consuming action, taking approx {1 + sleep_time} seconds')
        sleep(1 + sleep_time)
        return text

    def concatenate(self, array: list[str], separator: str = ', ') -> str:
        print(f'{self.agent_id} executing concatenate with params: {array}, {separator}')
        return separator.join(array)

    async def sample_stream(self):
        yield b'sampleStream data'

    def receive_message(self, message: Message):
        super().receive_message(message)
        print(f'{self.agent_id} received message: {message}')
