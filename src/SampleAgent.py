
from src import AbstractAgent
from Models import Message, StreamDescription


class SampleAgent(AbstractAgent):
    """
    Sample Agent class that inherits from AbstractAgent.
    Prints some information when receiving messages or executing actions.
    """

    def __init__(self, **kwargs):
        super(SampleAgent, self).__init__(**kwargs)
        self.add_action(
            name='sampleAction1',
            parameters={'param1': {'type': 'String', 'required': 'true'}, 'param2': {'type': 'Int', 'required': 'true'}},
            result='String',
            callback=self.sample_action_1
        )
        self.add_action(
            name='add',
            parameters={'x': {'type': 'Int', 'required': 'true'}, 'y': {'type': 'Int', 'required': 'true'}},
            result='Int',
            callback=self.add
        )
        self.add_action(
            name='timeConsumingAction',
            parameters={'text': {'type': 'String', 'required': 'true'}, 'time_offset': {'type': 'Int', 'required': 'true'}},
            result='String',
            callback=self.time_consuming_action
        )
        self.add_stream(
            name='sampleStream',
            mode=StreamDescription.Mode.GET,
            callback=self.sample_stream
        )

    def sample_action_1(self, param1: str, param2: int) -> str:
        return f'{self.agent_id} executed sampleAction1 with params: {param1}, {param2}'

    def add(self, x: int, y: int) -> int:
        print(f'{self.agent_id} executed add with params: {x}, {y}')
        try:
            return int(x) + int(y)
        except ValueError:
            return 0

    def time_consuming_action(self, text: str, time_offset: str = 0) -> str:
        time_offset = int(time_offset)
        print(f'{self.agent_id} executing time_consuming action, taking approx {60 + time_offset} seconds')
        from time import sleep
        sleep(60 + time_offset)
        return f'{text}, {time_offset}'

    async def sample_stream(self):
        yield b'sampleStream data'

    def receive_message(self, message: Message):
        super().receive_message(message)
        print(f'{self.agent_id} received message: {message}')
